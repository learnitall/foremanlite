#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test foremanlite.logging module."""
import pytest

import foremanlite.logging


@pytest.fixture
def _do_teardown_fixture():
    yield
    foremanlite.logging.teardown()


def test_value_error_raised_if_file_path_not_given_for_setup(
    _do_teardown_fixture,
):
    """Test `ValueError` raised if `file_path` is not given with `use_file`."""

    with pytest.raises(ValueError):
        foremanlite.logging.setup(use_file=True, file_path=None)

    with pytest.raises(ValueError):
        foremanlite.logging.setup(use_file=True, file_path=1)

    foremanlite.logging.setup(use_file=False, file_path=None)


def test_get_gets_a_child_of_the_base_logger(_do_teardown_fixture):
    """Test that `get` returns a child of the base logger."""

    foremanlite.logging.setup(use_stream=True)
    logger = foremanlite.logging.get("test")

    assert logger.name == foremanlite.logging.BASENAME + ".test"
    assert logger.hasHandlers()
