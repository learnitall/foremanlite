#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name,unused-argument
"""Test contents of foremanlite.store."""
import time

import pytest

import foremanlite.logging
from foremanlite.store import get_cache, start_cache, teardown_cache

CACHE_CONTENT = "hi there"
CACHE_FILES = {
    "test.txt": "hi there",
    "file1.txt": "I am file one",
}


@pytest.fixture()
def logfix():
    """Setup and teardown logging for each test."""

    foremanlite.logging.setup(verbose=True, use_stream=True)
    yield
    foremanlite.logging.teardown()


@pytest.fixture()
def contentdir(tmpdir):
    """Get a temporary directory with content."""

    for filename, content in CACHE_FILES.items():
        (tmpdir / filename).write_text(content, "utf-8")
    yield tmpdir


def test_filesystem_cache_will_use_cache_on_multiple_reads(logfix, contentdir):
    """Test filesystem cache will use cache for subsequent reads."""

    start_cache(contentdir)
    cache = get_cache()
    assert cache is not None
    filename, content = list(CACHE_FILES.items())[0]
    assert cache.read_file(filename).decode("utf-8") == content
    entry = cache.is_cached(contentdir / filename)
    assert entry is not None
    assert entry.decode("utf-8") == content
    assert cache.read_file(filename).decode("utf-8") == content
    teardown_cache()


def test_filesystem_cache_can_check_for_dirty_files(logfix, contentdir):
    """Test filesystem cache will detect dirty files."""

    start_cache(contentdir)
    cache = get_cache()
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
