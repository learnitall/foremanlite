#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tools for reading and caching data from the local filesystem."""
import hashlib
import logging
import os
import threading
import typing as t
from pathlib import Path

from jinja2 import Template
from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from foremanlite.logging import get as get_logger

SHA256 = t.NewType("SHA256", str)


class _FSEventHandler(FileSystemEventHandler):
    """Event handler for our cache's filesystem watchdog."""

    def __init__(self, cache: "FileSystemCache"):
        super().__init__()
        self.cache = cache

    def on_modified(self, event: FileModifiedEvent):
        """Callback for modified event."""
        if not event.is_directory:
            path = Path(event.src_path)
            key = self.cache.get_key(path)

            with self.cache.lock:
                entry = self.cache.cache.get(key, None)
                if entry is not None:
                    self.cache.logger.debug(f"Got dirty file: {str(path)}")
                    self.cache.cache[key] = (entry[0], True)


class FileSystemCache:
    """
    Get and cache files from the filesystem.

    Parameters
    -----------
    root_dir : str
        Directory to serve files out of.

    Raises
    ------
    ValueError
        if dir does not exist
    """

    def __init__(self, root_dir: str):
        self.root: Path = Path(root_dir)
        # Filename hash: content, is dirty
        self.cache: t.Dict[SHA256, t.Tuple[bytes, bool]] = {}
        self.lock: threading.Lock = threading.Lock()
        self.logger: logging.Logger = get_logger("FileSystemCache")
        self.observer = Observer()

        self.logger.info(f"Caching files from '{self.root}'")

    def start_watchdog(self):
        """Start watchdog service to detect dirty cache files."""

        self.observer.schedule(
            _FSEventHandler(self), self.root, recursive=True
        )
        self.observer.start()
        self.logger.info("Started filesystem cache watchdog")

    def stop_watchdog(self):
        """Stop the watchdog service."""

        self.logger.info("Stopping filesystem cache watchdog")
        self.observer.stop()
        self.observer.join()

    @staticmethod
    def compute_sha256(content: bytes) -> SHA256:
        """Get the SHA256 for the given content."""

        return SHA256(hashlib.sha256(content).hexdigest())

    def get_key(self, path: Path) -> SHA256:
        """
        Get cache key for the given path object.

        Parameters
        ----------
        path : Path

        Returns
        -------
        SHA256
        """

        return self.compute_sha256(str(path).encode("utf-8"))

    def get(self, path: Path) -> t.Optional[bytes]:
        """
        Check if given Path is cached, returning its content if it is.

        If the given path is not cached, return `None`

        Parameters
        ----------
        fn: str
            Filename of file to read from cache.

        Returns
        -------
        str
        """

        entry = self.cache.get(self.get_key(path))
        if entry is None:
            return None

        content, dirty = entry
        if not dirty:
            return content

        return None

    def put(self, path: Path, content: t.Optional[bytes] = None):
        """
        Add the given path and its contents to the cache.

        Parameters
        ----------
        path : Path
            path object representing file to cache
        content: bytes, optional
            contents of the file at the given path, if available.
            If not available, file will be read. This assumes the
            given content is the same as the actual file's content
            on disk.
        """

        if content is None:
            content = path.read_bytes()
        self.logger.debug(
            f"Caching {str(path)} ({str(self.compute_sha256(content))})"
        )
        self.cache[self.get_key(path)] = (
            content,
            False,
        )


class DataFile:
    """
    Wrap a pathlib.Path instance with helpful utility methods.

    Parameters
    ----------
    path : Path
        Wrapped pathlib.Path instance to work with.
    cache : FileSystemCache, optional
        If available, FileSystemCache to pull cached content from.
    """

    __slots__ = ("path", "cache")

    def __init__(self, path: Path, cache: t.Optional[FileSystemCache] = None):
        self.path: Path = path
        self.cache: t.Optional[FileSystemCache] = cache

    def validate(self):
        """
        Check that the data file is safe to read.

        The following checks are performed:

        * Path exists
        * Path is a file
        * Path is not relative
        * Path is not symbolic link
        * Path is readable

        Raises
        ------
        ValueError
            if validation fails
        """

        checks = (
            # function to check if true, error message
            (lambda p: p.exists(), "Path does not exist"),
            (lambda p: p.is_file(), "Path is not a file"),
            (lambda p: str(p.resolve()) == str(p), "Path is relative"),
            (lambda p: not p.is_symlink(), "Path is a symlink"),
            (lambda p: os.access(p, os.R_OK), "Path is not readable"),
        )

        for check, msg in checks:
            if not check(self.path):
                raise ValueError(f"{msg}: {self.path}")

    def read(self) -> bytes:
        """
        Read the data file and return its contents.

        If the file cannot be read, a ValueError is raised.
        Inherently calls `validate`
        """

        self.validate()
        if self.cache is not None:
            cached = self.cache.get(self.path)
            if cached is not None:
                return cached
            content = self.path.read_bytes()
            self.cache.put(self.path, content)

        return self.path.read_bytes()


class RenderFuncCallable(t.Protocol):
    """
    Type definition for template render function.

    See https://newbedev.com/
    python-typing-signature-typing-callable-for-function-with-kwargs
    """

    def __call__(self, content: str, **context: t.Any) -> str:
        ...


class DataJinjaTemplate(DataFile):
    """
    Wrap a jinja template with helpful utility methods.

    Note that if the wrapped Path does not point to a jinja
    template, this class will act the same as `DataFile`.
    The `render` method will behave the same as `read`, just
    with extra steps.

    Parameters
    ----------
    path : Path
        Wrapped pathlib.Path instance to work with.
    cache : FileSystemCache, optional
        If available, FileSystemCache to pull cached content from.
    render_func : RenderFuncCallable, optional
        Function to use in order to render the template. Defaults
        to the static method `render_jinja`, which uses
        `jinja2.Template`. Compatible functions take the string
        content of a template as the first argument and any
        kwargs given are used as variables for the template.
    """

    def __init__(
        self,
        path: Path,
        cache: t.Optional[FileSystemCache] = None,
        render_func: RenderFuncCallable = None,
    ):
        super().__init__(path, cache)
        if render_func is None:
            self._render_func = self.render_jinja
        else:
            self._render_func = render_func

    @staticmethod
    def render_jinja(content: str, **context: t.Any) -> str:
        """Render the given jinja2 template using kwargs as vars."""

        return Template(content).render(**context)

    def render_func(self, *args, **kwargs) -> str:
        """
        Pass given args and kwargs to stored render function.

        Given render functions are static, but some type checkers
        struggle to understand that (i.e. pylance). Having this wrapper
        method helps get around false-positive type issues.
        """

        return self._render_func(*args, **kwargs)

    def render(self, **context: t.Any) -> bytes:
        """
        Read the template from disk and render using given variables.

        Parameters
        ----------
        context : any
            Variables to pass to the template, given as kwargs.

        Raises
        ------
        ValueError
            If the file cannot be read
        """

        content = self.read().decode("utf-8")
        return self.render_func(content, **context).encode("utf-8")
