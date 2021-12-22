#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=unused-argument, redefined-outer-name
"""Test functionality in formanlite.store module."""
import os
import subprocess

from pytest_redis import factories

from foremanlite.store import RedisMachineStore


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


def test_redis_machine_store_does_not_fail_with_empty_db(
    logfix, my_redisdb, machine_factory
):
    """Test RedisMachineStore can handle working with an empty database."""

    assert my_redisdb.get(RedisMachineStore.MACHINES_KEY) is None

    store = RedisMachineStore(redis_conn=my_redisdb)
    store.get(name="not there")

    machine = machine_factory()
    store.put(machine)


def test_redis_machine_store_can_put_and_get(
    logfix, my_redisdb, machine_factory
):
    """Test the RedisMachineStore can put and get on a new db."""

    store = RedisMachineStore(redis_conn=my_redisdb)
    machine = machine_factory()
    store.put(machine)

    assert my_redisdb.get(store.MACHINES_KEY) is not None
    assert store.get(name=machine.name) == {machine}


def test_redis_machine_store_can_get_machines_by_attr(
    logfix, my_redisdb, machine_factory
):
    """Test the RedisMachineStore can get machines by matching attrs."""

    store = RedisMachineStore(redis_conn=my_redisdb)
    machines = [machine_factory(provision=True) for _ in range(5)]
    for machine in machines:
        store.put(machine)

    assert store.get(provision=True) == set(machines)
    assert store.get(provision=False) == set()


def test_redis_machine_store_can_list_all_machines(
    logfix, my_redisdb, machine_factory
):
    """Test the RedisMachineStore can return all machines in the store."""

    store = RedisMachineStore(redis_conn=my_redisdb)
    machine_pt = [machine_factory(provision=True) for _ in range(5)]
    machine_pf = [machine_factory(provision=False) for _ in range(5)]
    machine_all = []
    machine_all.extend(machine_pt)
    machine_all.extend(machine_pf)
    tuple(map(store.put, machine_all))

    assert store.all() == set(machine_all)
    assert store.get(provision=True).issubset(set(machine_all))
