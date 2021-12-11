# -*- coding: utf-8 -*-
"""Options for storing and retrieving information about a machine."""
from abc import ABC, abstractmethod
import typing as t
import hashlib
import os
from pathlib import Path
from foremanlite.machine import Machine, Mac


SHA256 = t.NewType('SHA256', str)


class FileSystemCache:
    """
    Get and cache files from the filesystem.

    Parameters
    -----------
    dir : str
        Directory to serve files out of.

    Raises
    ------
    ValueError
        if dir does not exist
    """

    def __init__(self, dir: str):
        self.dir: Path = Path(dir)
        # Filename sha: (content, content sha), is dirty
        self.cache: dict[SHA256, t.Tuple[bytes, SHA256, bool]] = {}

    @staticmethod
    def compute_sha256(content: bytes) -> SHA256:
        """Get the SHA256 for the given content."""

        return SHA256(
            hashlib.sha256(content).hexdigest()
        )
    
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

        return self.compute_sha256(str(path).encode('utf-8'))

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
            (lambda p: p.exists(), 'Path does not exist'),
            (lambda p: p.is_file(), 'Path is not a file'),
            (lambda p: not p.is_relative(), 'Path is relative'),
            (lambda p: not p.is_symlink(), 'Path is a symlink'),
            (lambda p: os.access(p, os.R_OK), 'Path is not readable')
        )
        for check, msg in checks:
            if not check(path):
                raise ValueError(msg)
    
    def pathify(self, fn: str) -> Path:
        """
        Get absolute path of given filename, relative to root dir.

        Parameters
        ----------
        fn : str
            Filename to get absolute path of.
            Expected to be relative to serving dir.
        
        Returns
        -------
        str
        """

        return self.dir.joinpath(fn)
    
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
        else:
            content, _, dirty = entry
            if not dirty:
                return content
    
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
        
        self.cache[self.get_cache_key(path)] = (
            content, self.compute_sha256(content), False
        )
    
    def read_file(self, fn: str) -> bytes:
        """
        Read the given file and return its contents.

        If the file is in the local cache, its contents will 
        be loaded from memory. If the file is not in the local cache,
        its contents will be added into memory.
        
        Parameters
        ----------
        fn : str
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

        target = self.pathify(fn)
        self.validate_path(target)

        cached = self.is_cached(target)
        if cached is not None:
            return cached
        
        content = target.read_bytes()
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


def get_cache() -> t.Optional[FileSystemCache]:
    """
    Return global FileSystemCache instance

    Returns
    -------
    None
        if no FileSystemCache has been created.
    FileSystemCache
    """
    
    global FILE_SYSTEM_CACHE
    return FILE_SYSTEM_CACHE


class BaseMachineStore(ABC):
    """ABC for a machine storage utility."""

    @abstractmethod
    def put(self, machine: Machine):
        """Put the given machine into the store."""

    @abstractmethod
    def get(self, mac: Mac) -> Machine:
        """Get the given machine from the store (by Mac)."""
