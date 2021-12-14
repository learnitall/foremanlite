#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=unused-argument
"""Test functionality in formanlite.store module."""
import random
import typing as t

from foremanlite.machine import Arch, Machine
from foremanlite.store import RedisMachineStore

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


def test_redis_machine_store_does_not_fail_with_empty_db(logfix, redisdb):
    """Test RedisMachineStore can handle working with an empty database."""

    assert redisdb.get(RedisMachineStore.MACHINES_KEY) is None

    store = RedisMachineStore(redis_conn=redisdb)
    store.get(name="not there")

    machine = get_test_machine()
    store.put(machine)


def test_redis_machine_store_can_put_and_get(logfix, redisdb):
    """Test the RedisMachineStore can put and get on a new db."""

    store = RedisMachineStore(redis_conn=redisdb)
    machine = get_test_machine()
    store.put(machine)

    assert redisdb.get(store.MACHINES_KEY) is not None
    assert store.get(name=machine.name) == {machine}


def test_redis_machine_store_can_get_machines_by_attr(logfix, redisdb):
    """Test the RedisMachineStore can get machines by matching attrs."""

    store = RedisMachineStore(redis_conn=redisdb)
    machines = [get_test_machine(provision=True) for _ in range(5)]
    for machine in machines:
        store.put(machine)

    assert store.get(provision=True) == set(machines)
    assert store.get(provision=False) == set()


def test_redis_machine_store_can_list_all_machines(logfix, redisdb):
    """Test the RedisMachineStore can return all machines in the store."""

    store = RedisMachineStore(redis_conn=redisdb)
    machine_pt = [get_test_machine(provision=True) for _ in range(5)]
    machine_pf = [get_test_machine(provision=False) for _ in range(5)]
    machine_all = []
    machine_all.extend(machine_pt)
    machine_all.extend(machine_pf)
    tuple(map(store.put, machine_all))

    assert store.all() == set(machine_all)
    assert store.get(provision=True).issubset(set(machine_all))
