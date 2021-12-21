#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Store shared fixtures for foremanlite tests."""
import random
import typing as t

import pytest

import foremanlite.logging
from foremanlite.machine import Arch, Machine

TEST_MACHINES: t.Dict[str, t.Sequence] = {
    "name": (
        "machine1",
        "mymachine",
        "testmachine",
    ),
    "mac": ("11:22:33:44:55:66", "de:ad:be:ef:11:22", "12:34:56:78:90:12"),
    "arch": tuple(e.value for e in Arch),
    "provision": (True, False),
}


@pytest.fixture()
def logfix():
    """Setup and teardown logging for each test."""

    foremanlite.logging.setup(verbose=True, use_stream=True)
    yield
    foremanlite.logging.teardown()


def get_test_machine(**kwargs) -> Machine:
    """
    Generate and return new random test Machine.

    kwargs can be used as universal overrides.
    """
    params: t.Dict[str, t.Any] = {
        key: random.choice(value) for key, value in TEST_MACHINES.items()
    }
    params.update(kwargs)

    return Machine(**params)


@pytest.fixture()
def machine_factory():
    """Return `get_test_machine` function for generating new Machines."""

    return get_test_machine
