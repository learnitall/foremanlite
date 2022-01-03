#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name,unused-argument
"""Test contents of foremanlite.fsdata module."""
import re
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


pytestmark = pytest.mark.usefixtures("logfix")


def populatedir(tmp: Path, files: t.Dict[str, str]):
    """Populate directory with given files."""

    for filename, content in files.items():
        file_path = tmp / filename
        file_path.touch()
        assert file_path.write_text(content, "utf-8") == len(content)


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


class TestFileSystemCache:
    """Test functionality of foremanlite.fsdata.FileSystemCache"""

    @staticmethod
    @given(
        files=st.dictionaries(
            keys=st_filename,
            values=st.text(),
        )
    )
    def test_filesystem_cache_can_get_and_put(files, cache_factory):
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

    @staticmethod
    @given(
        files_paired=st.dictionaries(
            keys=st_filename, values=st_paired_content, min_size=1
        )
    )
    @settings(max_examples=15)
    def test_filesystem_cache_can_detect_dirty_files(
        files_paired, cache_factory
    ):
        """Test the filesystem cache can detect if a file is dirty."""

        cache: FileSystemCache
        contentdir: Path
        with cache_factory() as (cache, contentdir):
            files = {
                filename: content[0]
                for filename, content in files_paired.items()
            }
            dirt = {
                filename: content[1]
                for filename, content in files_paired.items()
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

    @staticmethod
    @given(
        files=st.dictionaries(
            keys=st_filename,
            values=st.text(min_size=1),
            min_size=1,
            max_size=1,
        )
    )
    def test_filesystem_cache_put_returns_false_when_file_is_too_big(
        files, cache_factory
    ):
        """Test the filesystem cache put returns False if file is too big."""

        cache: FileSystemCache
        contentdir: Path
        with cache_factory() as (cache, contentdir):
            populatedir(contentdir, files)
            cache.max_file_size_bytes = 0
            assert not cache.put(contentdir / list(files.keys())[0])


class TestDataFile:
    """Test functionality of foremanlite.fsdata.DataFile"""

    @staticmethod
    def test_datafile_validate_method_correctly_determines_file_can_be_read(
        contentdir_factory,
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

    @staticmethod
    @given(
        files=st.dictionaries(
            keys=st_filename,
            values=st.text(),
            min_size=1,
        )
    )
    def test_datafile_can_read_with_no_cache(files, contentdir_factory):
        """Test DataFile can read a file without a cache instance."""

        contentdir: Path = contentdir_factory()
        populatedir(contentdir, files)
        for filename, content in files.items():
            path = contentdir / filename
            assert DataFile(path).read().decode("utf-8") == content

    @staticmethod
    @given(
        files_paired=st.dictionaries(
            keys=st_filename, values=st_paired_content, min_size=1
        )
    )
    def test_datafile_can_read_with_a_cache(files_paired, cache_factory):
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


class TestDataJinjaTemplate:
    """Test functionality of foremanlite.fsdata.DataJinjaTemplate."""

    @staticmethod
    @given(
        template_dict=st.dictionaries(
            keys=st.from_regex(re.compile(r"^[a-zA-Z]+$"), fullmatch=True),
            values=st.text(min_size=1)
            | st.integers()
            | st.booleans()
            | st.none(),
        )
    )
    def test_data_jinja_template_can_render_jinja_template(
        template_dict, contentdir_factory
    ):
        """Test DataJinjaTemplate can be used to render a jinja2 template."""

        contentdir: Path = contentdir_factory()
        template_text = ""
        result = ""
        for key, value in template_dict.items():
            # simulate escaping
            template_text += "{{" + key + "}}"
            result += str(value)
        path = contentdir / "template.j2"
        path.write_text(template_text)
        assert (
            DataJinjaTemplate(path).render(**template_dict).decode("utf-8")
            == result
        )

    @staticmethod
    def test_data_jinja_template_can_use_custom_render_func(
        contentdir_factory,
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
