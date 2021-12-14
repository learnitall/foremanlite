#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Store shared fixtures for foremanlite tests."""
import pytest

import foremanlite.logging


@pytest.fixture()
def logfix():
    """Setup and teardown logging for each test."""

    foremanlite.logging.setup(verbose=True, use_stream=True)
    yield
    foremanlite.logging.teardown()
