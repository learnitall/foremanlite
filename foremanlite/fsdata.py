#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tools for reading and caching data from the local filesystem."""
import hashlib
import logging
import os
import typing as t
from pathlib import Path

from jinja2 import Template

from foremanlite.logging import get as get_logger

SHA256 = t.NewType("SHA256", str)


class FileSystemCache:
    """
    Get and cache files from the filesystem.

    Parameters
    -----------
    root_dir : str or Path
        Directory to serve files out of.
    max_file_size_bytes : int, optional
        Set an upper limit on the size of files (in bytes) that
        can be cached. If omitted, no restriction will be used.

    Raises
    ------
    ValueError
        if dir does not exist
    """

    __slots__ = ["root", "cache", "logger", "max_file_size_bytes"]

    def __init__(
        self,
        root_dir: t.Union[str, Path],
        max_file_size_bytes: t.Optional[int] = None,
    ):
        self.root: Path = Path(root_dir)
        # Filename hash: content, last modified time in seconds
        self.cache: t.Dict[SHA256, t.Tuple[bytes, int]] = {}
        self.logger: logging.Logger = get_logger("FileSystemCache")
        self.max_file_size_bytes = max_file_size_bytes

        self.logger.info(f"Caching files from {repr(str(self.root))}")

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

    def is_dirty(
        self,
        path: Path,
        entry: t.Optional[t.Tuple[bytes, int]] = None,
        stat: t.Optional[os.stat_result] = None,
    ) -> bool:
        """
        Check if given path has changed on disk since being cached.

        If the given path is not in the cache, then a ValueError is raised.

        If the current last modified time cannot be determined for the given
        path, then an `OSError`, or subclass thereof, is raised.

        Parameters
        ----------
        path : Path
        entry : tuple of str and int, optional
            If the entry for the given path in the cache has already been
            retrieved for the given Path, then it can be provided here.
        stat : os.stat_result, optional
            If the `os.stat_result` has already been retrieved for the given
            Path, then it can be provided here.

        Returns
        -------
        bool

        Raises
        ------
        ValueError
        OSError
        """

        if entry is None:
            entry = self.cache.get(self.get_key(path))
        if entry is None:
            raise ValueError(
                "Was requested to check if given path is dirty, but file is "
                f"not present in the cache: {repr(str(path))}",
            )
        _, last_known_mtime = entry

        if stat is None:
            stat = path.stat()
        mtime = stat.st_mtime_ns

        if last_known_mtime < mtime:
            self.logger.info("Found dirty file in cache: %s", repr(str(path)))
            return True
        return False

    def get(self, path: Path) -> t.Optional[bytes]:
        """
        Check if given Path is cached, returning its content if it is.

        If the given path is not cached, return `None`. If the given
        file is cached, but has changed on disk, this method will
        attempt to update the cache with the file's current contents
        (using `put`). If this fails, an `OSError` will be raised.

        If the given path is not in the cache, and the last known
        modified time of the given file is unable to be determined,
        then an OSError (or subclass thereof) is raised.

        Parameters
        ----------
        fn: str
            Filename of file to read from cache.

        Returns
        -------
        str

        Raises
        ------
        OSError
        """

        entry = self.cache.get(self.get_key(path))
        if entry is None:
            return None

        content, _ = entry

        if self.is_dirty(path, entry=entry):
            success = self.put(path)
            if not success:
                raise OSError(
                    f"Unable to update dirty file in cache: {repr(str(path))}"
                )
            return self.get(path)
        return content

    def put(self, path: Path, content: t.Optional[bytes] = None) -> bool:
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

        Returns
        -------
        bool
            True if file was cached successfully, otherwise False.
            A file will not be cached successfully if its size in
            bytes is greater than the set max limit. See the
            `max_file_size_bytes` parameter.

        Raises
        ------
        OSError
            If the given Path cannot be read successfully.
        """

        path_stat: t.Optional[os.stat_result] = None
        if self.max_file_size_bytes is not None:
            path_stat = path.stat()
            size_bytes = path_stat.st_size if content is None else len(content)
            if size_bytes > self.max_file_size_bytes:
                msg = (
                    "Got request to cache file greater than max size "
                    f"{self.max_file_size_bytes}: {repr(str(path))} "
                    f"({size_bytes} bytes)"
                )
                self.logger.debug(msg)
                return False

        if content is None:
            content = path.read_bytes()
        if path_stat is None:
            path_stat = path.stat()

        mtime = path_stat.st_mtime_ns

        self.logger.debug(
            f"Caching {repr(str(path))}: "
            f"SHA256: {str(self.compute_sha256(content))}), "
            f"mtime_ns: {mtime}"
        )
        self.cache[self.get_key(path)] = (content, mtime)
        return True


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


class JinjaRenderFuncCallable(t.Protocol):
    """
    Type definition for jinja render function.

    See https://newbedev.com/
    python-typing-signature-typing-callable-for-function-with-kwargs
    """

    def __call__(self, source: str, **context: t.Any) -> str:
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
    jinja_render_func : JinjaRenderFuncCallable, optional
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
        jinja_render_func: t.Optional[JinjaRenderFuncCallable] = None,
    ):
        super().__init__(path, cache)
        if jinja_render_func is None:
            self._jinja_render_func = self.render_jinja
        else:
            self._jinja_render_func = jinja_render_func

    @staticmethod
    def render_jinja(source: str, **context: t.Any) -> str:
        """Render the given jinja2 template using kwargs as vars."""

        return Template(source).render(**context)

    def jinja_render_func(self, *args, **kwargs) -> str:
        """
        Pass given args and kwargs to stored jinja render function.

        Given render functions are static, but some type checkers
        struggle to understand that (i.e. pylance). Having this wrapper
        method helps get around false-positive type issues.
        """

        return self._jinja_render_func(*args, **kwargs)

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

        logger = get_logger("DataJinjaTemplate")
        logger.info(f"Rendering {self.path} with args: {context}")
        content = self.read().decode("utf-8")
        rendered = self.jinja_render_func(content, **context)
        logger.debug(
            f"Result of rendering {self.path} with args {context}: {rendered}"
        )
        return rendered.encode("utf-8")
