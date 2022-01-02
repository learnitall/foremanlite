#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Store shared fixtures for foremanlite tests."""
import os
import random
import re
import subprocess
import typing as t

import pytest
from hypothesis import HealthCheck, assume, settings
from hypothesis import strategies as st
from pytest_redis import factories

import foremanlite.logging
from foremanlite.machine import SHA256, Arch, Machine, get_uuid

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
)
settings.load_profile("suppress_too_slow")


@st.composite
def machine_strategy(draw):
    """Hypothesis strategy to generate Machine instances."""

    mac = st.from_regex(
        re.compile(r"([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}"), fullmatch=True
    )
    arch = st.sampled_from(Arch)
    name = st.one_of(st.none(), st.text())
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


TEST_MACHINES: t.Dict[str, t.Sequence] = {
    "name": (
        "machine1",
        "mymachine",
        "testmachine",
    ),
    "mac": ("11:22:33:44:55:66", "de:ad:be:ef:11:22", "12:34:56:78:90:12"),
    "arch": tuple(e for e in Arch),
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


@pytest.fixture()
def unique_machine_factory():
    """Generate and return a unique list of machines."""

    max_combinations = len(TEST_MACHINES["arch"]) * len(TEST_MACHINES["mac"])

    def _unique_machine_factory(num: int, **kwargs):
        if num > max_combinations:
            raise ValueError(
                f"Cannot generate more than {max_combinations} of unique "
                f"machines at once. Was requested to generate {num}"
            )

        uuids: t.List[SHA256] = []
        machines: t.List[Machine] = []
        while len(machines) < num:
            new_machine = get_test_machine(**kwargs)
            new_uuid = get_uuid(machine=new_machine)
            if new_uuid not in uuids:
                uuids.append(new_uuid)
                machines.append(new_machine)

        return machines

    return _unique_machine_factory


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
