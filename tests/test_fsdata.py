#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name,unused-argument
"""Test contents of foremanlite.fsdata module."""
import re
import shutil
import time
import typing as t
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from foremanlite.fsdata import DataFile, DataJinjaTemplate, FileSystemCache

st_filename = st.from_regex(re.compile(r"^[a-z0-9]+$"), fullmatch=True)
st_paired_content = st.tuples(st.text(), st.text()).filter(
    lambda x: (not (len(x[0]) == 0 and len(x[1]) == 0) and not x[0] == x[1])
)


def populatedir(tmp: Path, files: t.Dict[str, str]):
    """Populate directory with given files."""

    for filename, content in files.items():
        file_path = tmp / filename
        file_path.touch()
        assert file_path.write_text(content, "utf-8") == len(content)


@pytest.fixture()
def contentdir_factory(tmp_path_factory):
    """
    Get a temporary directory for cacheable content.

    To add cacheable content to the directory, use hypothesis
    to generate some text for you.

    This fixture is needed because hypothesis is incompatible
    with function-scoped fixtures.
    """

    def _create():
        """Create the unique temporary directory"""
        tmpdir: Path = tmp_path_factory.mktemp(
            basename="fsdata", numbered=True
        )
        if len(list(tmpdir.iterdir())) > 0:
            shutil.rmtree(tmpdir)
        return tmpdir

    return _create


@pytest.fixture()
def cache_factory(contentdir_factory):
    """Create and teardown a FileSystemCache instance."""

    class _Create:
        """Context manager for the file system cache"""

        def __init__(self):
            self.contentdir: Path = contentdir_factory()
            self.cache = FileSystemCache(self.contentdir, polling_interval=0.1)

        def __enter__(self):
            self.cache.start_watchdog()
            return self.cache, self.contentdir

        def __exit__(self, *_):
            self.cache.stop_watchdog()

    return _Create


@given(
    files=st.dictionaries(
        keys=st_filename,
        values=st.text(),
    )
)
def test_filesystem_cache_can_get_and_put(files, logfix, cache_factory):
    """Test the filesystem cache can store a file and read it back."""

    cache: FileSystemCache
    contentdir: Path
    with cache_factory() as (cache, contentdir):
        populatedir(contentdir, files)
        for filename in files:
            target_file = contentdir / filename
            content = target_file.read_bytes()
            cache.put(target_file, content)
            assert content == cache.get(target_file)


@given(
    files_paired=st.dictionaries(
        keys=st_filename, values=st_paired_content, min_size=1
    )
)
@settings(max_examples=15)
def test_filesystem_cache_can_detect_dirty_files(
    files_paired, logfix, cache_factory
):
    """Test the filesystem cache can detect if a file is dirty."""

    cache: FileSystemCache
    contentdir: Path
    with cache_factory() as (cache, contentdir):
        files = {
            filename: content[0] for filename, content in files_paired.items()
        }
        dirt = {
            filename: content[1] for filename, content in files_paired.items()
        }
        populatedir(contentdir, files)
        for filename in files:
            target_file = contentdir / filename
            cache.put(target_file)
            target_file.write_text(dirt[filename])
            waited_time = 0
            while cache.get(target_file) is not None:
                time.sleep(0.05)
                waited_time += 0.05
                assert waited_time < 0.5


@given(
    files=st.dictionaries(
        keys=st_filename,
        values=st.text(min_size=1),
        min_size=1,
        max_size=1,
    )
)
def test_filesystem_cache_put_returns_false_when_file_is_too_big(
    files, logfix, cache_factory
):
    """Test the filesystem cache put returns False if file is too big."""

    cache: FileSystemCache
    contentdir: Path
    with cache_factory() as (cache, contentdir):
        populatedir(contentdir, files)
        cache.max_file_size_bytes = 0
        assert not cache.put(contentdir / list(files.keys())[0])


def test_datafile_validate_method_correctly_determines_file_can_be_read(
    logfix, contentdir_factory
):
    """Determine datatest.validate determines if Path can be read."""

    contentdir: Path = contentdir_factory()
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


@given(
    files=st.dictionaries(
        keys=st_filename,
        values=st.text(),
        min_size=1,
    )
)
def test_datafile_can_read_with_no_cache(files, logfix, contentdir_factory):
    """Test DataFile can read a file without a cache instance."""

    contentdir: Path = contentdir_factory()
    populatedir(contentdir, files)
    for filename, content in files.items():
        path = contentdir / filename
        assert DataFile(path).read().decode("utf-8") == content


@given(
    files_paired=st.dictionaries(
        keys=st_filename, values=st_paired_content, min_size=1
    )
)
def test_datafile_can_read_with_a_cache(files_paired, logfix, cache_factory):
    """Test DataFile can read a file using a cache instance."""

    cache: FileSystemCache
    contentdir: Path
    with cache_factory() as (cache, contentdir):
        # needed for this test, as we change file contents
        # and don't want the file to marked as dirty
        cache.stop_watchdog()
        for filename, (content, other_content) in files_paired.items():
            path = contentdir / filename
            path.write_text(content)
            data_file = DataFile(path, cache=cache)
            assert data_file.read().decode("utf-8") == content
            path.write_text(other_content)
            assert data_file.read().decode("utf-8") == content


def test_data_jinja_template_can_render_jinja_template(
    logfix, contentdir_factory
):
    """Test DataJinjaTemplate can be used to render a jinja2 template."""

    contentdir: Path = contentdir_factory()
    template_name = "template.txt"
    template_text = "{{ greeting }} {{ name }}{{ punctuation }}"
    context = {"greeting": "hello", "name": "george", "punctuation": "?"}
    result = "hello george?"
    path = contentdir / template_name
    path.write_text(template_text)
    assert DataJinjaTemplate(path).render(**context).decode("utf-8") == result


def test_data_jinja_template_can_use_custom_render_func(
    logfix, contentdir_factory
):
    """Test DataJinjaTemplate can use a custom render function."""

    contentdir: Path = contentdir_factory()
    path = contentdir / "mytemplate.txt"
    path.write_text("content that will not be seen")
    result = "rendered"

    def _my_render_func(source, **context) -> str:
        """Dumb render func that just returns static content."""
        return result

    assert (
        DataJinjaTemplate(path, jinja_render_func=_my_render_func)
        .render(unused_var=True)
        .decode("utf-8")
        == result
    )
