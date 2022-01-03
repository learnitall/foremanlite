#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Store shared fixtures for foremanlite tests."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from hypothesis import HealthCheck, assume, settings
from hypothesis import strategies as st
from pytest_redis import factories

import foremanlite.logging
from foremanlite.machine import Arch, Machine

# Sometimes when running tests on a laptop can run into this
# health check, (generating machines is really expensive), so
# let's disable it by default.
settings.register_profile(
    "suppress_too_slow",
    suppress_health_check=(
        HealthCheck.too_slow,
        HealthCheck.function_scoped_fixture,
    ),
    deadline=None,
    max_examples=15,
)
settings.load_profile("suppress_too_slow")


@st.composite
def machine_strategy(draw):
    """Hypothesis strategy to generate Machine instances."""

    mac = st.from_regex(
        re.compile(r"([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}"), fullmatch=True
    )
    arch = st.sampled_from(Arch)
    name = st.one_of(st.none(), st.text(min_size=1))
    provision = st.one_of(st.none(), st.booleans())

    machine = draw(
        st.builds(Machine, mac=mac, arch=arch, name=name, provision=provision)
    )

    return machine


@st.composite
def two_unique_machines_strategy(draw):
    """Hypothesis strategy to generate two unique Machine instances."""

    machine_one = draw(machine_strategy())
    machine_two = draw(machine_strategy())
    for key in machine_one.dict():
        assume(getattr(machine_one, key) != getattr(machine_two, key))
    return machine_one, machine_two


@pytest.fixture()
def logfix():
    """Setup and teardown logging for each test."""

    foremanlite.logging.setup(verbose=True, use_stream=True)
    yield
    foremanlite.logging.teardown()


@pytest.fixture
def do_log_teardown():
    """
    Same as logfix, except we only perform the teardown step.

    Used when a test sets up its own logging.
    """

    yield
    foremanlite.logging.teardown()


def get_redis_exec():
    """
    Find path to redis-server on the system using `which`.

    Can override with env var REDIS_EXEC.
    """

    return os.environ.get(
        "REDIS_EXEC",
        subprocess.run(
            ["which", "redis-server"], capture_output=True, check=True
        ).stdout.decode("utf-8"),
    ).strip()


REDIS_EXEC = get_redis_exec()
my_redis_proc = factories.redis_proc(executable=REDIS_EXEC)
my_redisdb = factories.redisdb("my_redis_proc")


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
