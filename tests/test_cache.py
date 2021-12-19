#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name,unused-argument
"""Test contents of foremanlite.store."""
import os
import time

import pytest

from foremanlite.cache import FileSystemCache

CACHE_CONTENT = "hi there"
CACHE_FILES = {
    "test.txt": "hi there",
    "file1.txt": "I am file one",
}


@pytest.fixture()
def contentdir(tmpdir):
    """Get a temporary directory with cacheable content."""

    for filename, content in CACHE_FILES.items():
        (tmpdir / filename).write_text(content, "utf-8")
    yield tmpdir


@pytest.fixture()
def cachefactory(contentdir):
    """Create and teardown a FileSystemCache instance."""

    cache = FileSystemCache(contentdir)
    cache.start_watchdog()
    yield cache, contentdir
    cache.stop_watchdog()


def test_filesystem_cache_will_use_cache_on_multiple_reads(
    logfix, cachefactory
):
    """Test filesystem cache will use cache for subsequent reads."""

    cache, contentdir = cachefactory
    assert cache is not None
    filename, content = list(CACHE_FILES.items())[0]
    assert cache.read_file(filename).decode("utf-8") == content
    entry = cache.is_cached(contentdir / filename)
    assert entry is not None
    assert entry.decode("utf-8") == content
    assert cache.read_file(filename).decode("utf-8") == content


def test_filesystem_cache_can_check_for_dirty_files(logfix, cachefactory):
    """Test filesystem cache will detect dirty files."""

    cache, contentdir = cachefactory
    assert cache is not None
    filename, content = list(CACHE_FILES.items())[0]
    assert cache.read_file(filename).decode("utf-8") == content
    entry = cache.is_cached(contentdir / filename)
    assert entry is not None and entry.decode("utf-8") == content

    new_content = "this is more content"
    (contentdir / filename).write_text(new_content, "utf-8")
    time.sleep(0.5)  # wait for watchdog to do its thing
    assert cache.read_file(filename).decode("utf-8") != content
    assert cache.read_file(filename).decode("utf-8") == new_content


def test_filesystem_cache_can_check_if_file_exists(logfix, cachefactory):
    """Test the filesystem cache can check if file exists by name."""

    cache, contentdir = cachefactory
    assert cache is not None
    for filename in CACHE_FILES:
        assert cache.file_exists(filename)
        cache.read_file(filename)
        os.remove(contentdir / filename)
        time.sleep(0.1)  # let watchdog update
        assert not cache.file_exists(filename)


def test_filesystem_cache_can_check_if_file_exists_no_watchdog(
    logfix, cachefactory
):
    """Test the fs cache (no watchdog) can check if file exists by name."""

    cache, contentdir = cachefactory
    assert cache is not None
    cache.stop_watchdog()
    for filename in CACHE_FILES:
        assert cache.file_exists(filename)
        cache.read_file(filename)
        os.remove(contentdir / filename)
        time.sleep(0.1)  # same behavior as previous test
        assert cache.file_exists(filename)
