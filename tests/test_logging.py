#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test foremanlite.logging module."""
import pytest

import foremanlite.logging

pytestmark = pytest.mark.usefixtures("do_log_teardown")


def test_value_error_raised_if_file_path_not_given_for_setup():
    """Test `ValueError` raised if `file_path` is not given with `use_file`."""

    with pytest.raises(ValueError):
        foremanlite.logging.setup(use_file=True, file_path=None)

    with pytest.raises(ValueError):
        foremanlite.logging.setup(use_file=True, file_path=1)  # type: ignore

    foremanlite.logging.setup(use_file=False, file_path=None)


def test_get_gets_a_child_of_the_base_logger():
    """Test that `get` returns a child of the base logger."""

    foremanlite.logging.setup(use_stream=True)
    logger = foremanlite.logging.get("test")

    assert logger.name == foremanlite.logging.BASENAME + ".test"
    assert logger.hasHandlers()
