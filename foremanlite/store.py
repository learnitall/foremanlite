# -*- coding: utf-8 -*-
"""Options for storing and retrieving information about a machine."""
import hashlib
import logging
import os
import threading
import typing as t
from abc import ABC, abstractmethod
from pathlib import Path

from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

from foremanlite.logging import get as get_logger
from foremanlite.machine import Mac, Machine

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
            key = self.cache.get_cache_key(path)

            with self.cache.lock:
                entry = self.cache.cache.get(key, None)
                if entry is not None:
                    self.cache.logger.debug(f"Got dirty file: {str(path)}")
                    self.cache.cache[key] = (entry[0], entry[1], True)


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
        # Filename hash: (content, content sha), is dirty
        self.cache: dict[SHA256, t.Tuple[bytes, SHA256, bool]] = {}
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

    def get_cache_key(self, path: Path) -> SHA256:
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

    @staticmethod
    def validate_path(path: Path):
        """
        Check that the given path is safe.

        * Path exists
        * Path is a file
        * Path is not relative
        * Path is not symbolic link
        * Path is readable

        Parameters
        ----------
        path : Path
            path to validate

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
            if not check(path):
                raise ValueError(f"{msg}: {path}")

    def pathify(self, filename: str) -> Path:
        """
        Get absolute path of given filename, relative to root dir.

        Parameters
        ----------
        filename : str
            Filename to get absolute path of.
            Expected to be relative to serving dir.

        Returns
        -------
        str
        """

        return self.root.joinpath(filename)

    def is_cached(self, path: Path) -> t.Optional[bytes]:
        """
        Check if given Path is cached, returning its content if it is.

        Parameters
        ----------
        fn: str
            Filename of file to read from cache.

        Returns
        -------
        str
        """

        entry = self.cache.get(self.get_cache_key(path))
        if entry is None:
            return None

        content, _, dirty = entry
        if not dirty:
            return content

        return None

    def add_to_cache(self, path: Path, content: bytes):
        """
        Add the given path and its contents to the cache.

        Parameters
        ----------
        path : Path
            path object representing file to cache
        content: bytes
            contents of the file at the given path
        """

        self.logger.debug(f"Caching {str(path)}")
        self.cache[self.get_cache_key(path)] = (
            content,
            self.compute_sha256(content),
            False,
        )

    def read_file(self, filename: str) -> bytes:
        """
        Read the given file and return its contents.

        If the file is in the local cache, its contents will
        be loaded from memory. If the file is not in the local cache,
        its contents will be added into memory.

        Parameters
        ----------
        filename : str
            Filename of file to read. Must be relative to root directory
            given to handler upon instantiation.

        Returns
        -------
        str

        Raises
        ------
        ValueError
            if path validate fails on given filename (see `validate_path`)
        """

        target = self.pathify(filename)
        self.validate_path(target)

        with self.lock:
            cached = self.is_cached(target)
            if cached is not None:
                return cached

        content = target.read_bytes()
        with self.lock:
            self.add_to_cache(target, content)

        return content


FILE_SYSTEM_CACHE: t.Optional[FileSystemCache] = None


def start_cache(*args, **kwargs):
    """
    Start the global file system cache.

    Given args and kwargs are passed directly to FileSystemCache init.
    """

    global FILE_SYSTEM_CACHE
    FILE_SYSTEM_CACHE = FileSystemCache(*args, **kwargs)
    FILE_SYSTEM_CACHE.start_watchdog()


def get_cache() -> t.Optional[FileSystemCache]:
    """
    Return global FileSystemCache instance

    Returns
    -------
    None
        if no FileSystemCache has been created.
    FileSystemCache
    """

    return FILE_SYSTEM_CACHE


def teardown_cache():
    """
    Teardown current filesystem cache.

    This is mainly used for testing purposes, but needs to be called
    before exit.
    """

    global FILE_SYSTEM_CACHE
    if FILE_SYSTEM_CACHE is None:
        return
    FILE_SYSTEM_CACHE.stop_watchdog()
    FILE_SYSTEM_CACHE = None


class BaseMachineStore(ABC):
    """ABC for a machine storage utility."""

    @abstractmethod
    def put(self, machine: Machine):
        """Put the given machine into the store."""

    @abstractmethod
    def get(self, mac: Mac) -> Machine:
        """Get the given machine from the store (by Mac)."""
