#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name,unused-argument
"""Test contents of foremanlite.fsdata module."""
import time
from pathlib import Path

import pytest

from foremanlite.fsdata import DataFile, DataJinjaTemplate, FileSystemCache

CACHE_FILES = {
    "test.txt": "hi there",
    "file1.txt": "I am file one",
}


@pytest.fixture()
def contentdir(tmpdir):
    """Get a temporary directory with cacheable content."""

    for filename, content in CACHE_FILES.items():
        (tmpdir / filename).write_text(content, "utf-8")
    yield Path(tmpdir)


@pytest.fixture()
def cachefactory(contentdir):
    """Create and teardown a FileSystemCache instance."""

    cache = FileSystemCache(contentdir)
    cache.start_watchdog()
    yield cache, contentdir
    cache.stop_watchdog()


def test_filesystem_cache_can_get_and_put(logfix, cachefactory):
    """Test the filesystem cache can store a file and read it back."""

    cache: FileSystemCache
    contentdir: Path
    cache, contentdir = cachefactory
    for filename in CACHE_FILES:
        target_file = contentdir / filename
        content = target_file.read_bytes()
        cache.put(target_file, content)
        assert content == cache.get(target_file)


def test_filesystem_cache_can_detect_dirty_files(logfix, cachefactory):
    """Test the filesystem cache can detect if a file is dirty."""

    cache: FileSystemCache
    contentdir: Path
    cache, contentdir = cachefactory
    for filename in CACHE_FILES:
        target_file = contentdir / filename
        cache.put(target_file)
        target_file.write_text(filename[::-1])
        time.sleep(0.1)  # make sure watchdog has time to catch up
        assert cache.get(target_file) is None


def test_datafile_validate_method_correctly_determines_file_can_be_read(
    logfix, contentdir
):
    """Determine datatest.validate determines if Path can be read."""

    invalidate_funcs = [
        (
            "exists",
            lambda: contentdir / "i_dont_exist",
            lambda p: p,
        ),
        ("is file", lambda: contentdir / "i_am_dir", lambda p: p.mkdir()),
        (
            "not relative",
            lambda: contentdir / "i_am_dir" / ".." / "a_file",
            lambda p: p.write_text("hey"),
        ),
        (
            "not symbolic",
            lambda: contentdir / "alink",
            lambda p: p.symlink_to("a linkable file"),
        ),
        (
            "is readable",
            lambda: contentdir / "a_file",
            lambda p: p.chmod(0o000),
        ),
    ]

    for name, path_gen, pre in invalidate_funcs:
        print(name)
        path: Path = path_gen()
        pre(path)
        with pytest.raises(ValueError):
            DataFile(path).validate()


def test_datafile_can_read_with_no_cache(logfix, cachefactory):
    """Test DataFile can read a file without a cache instance."""

    contentdir: Path
    _, contentdir = cachefactory
    for filename, content in CACHE_FILES.items():
        path = contentdir / filename
        assert DataFile(path).read().decode("utf-8") == content


def test_datafile_can_read_with_a_cache(logfix, cachefactory):
    """Test DataFile can read a file using a cache instance."""

    cache: FileSystemCache
    contentdir: Path
    cache, contentdir = cachefactory
    # needed for this test, as we change file contents
    # and don't want the file to marked as dirty
    cache.stop_watchdog()
    for filename, content in CACHE_FILES.items():
        path = contentdir / filename
        data_file = DataFile(path, cache=cache)
        assert data_file.read().decode("utf-8") == content
        path.write_text(content[::-1])
        assert data_file.read().decode("utf-8") == content


def test_data_jinja_template_can_render_jinja_template(logfix, contentdir):
    """Test DataJinjaTemplate can be used to render a jinja2 template."""

    template_name = "template.txt"
    template_text = "{{ greeting }} {{ name }}{{ punctuation }}"
    context = {"greeting": "hello", "name": "george", "punctuation": "?"}
    result = "hello george?"
    path = contentdir / template_name
    path.write_text(template_text)
    assert DataJinjaTemplate(path).render(**context).decode("utf-8") == result


def test_data_jinja_template_can_use_custom_render_func(logfix, contentdir):
    """Test DataJinjaTemplate can use a custom render function."""

    path = contentdir / "mytemplate.txt"
    path.write_text("content that will not be seen")
    result = "rendered"

    def _my_render_func(source, **context) -> str:
        """Dumb render func that just returns static content."""
        return result

    assert (
        DataJinjaTemplate(path, render_func=_my_render_func)
        .render(unused_var=True)
        .decode("utf-8")
        == result
    )
