#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=unused-argument, redefined-outer-name
"""Test functionality in formanlite.store module."""
import pytest

from foremanlite.machine import SHA256, get_uuid
from foremanlite.store import RedisMachineStore


def test_redis_machine_store_does_not_fail_with_empty_db(
    logfix, my_redisdb, machine_factory
):
    """Test RedisMachineStore can handle working with an empty database."""

    assert my_redisdb.get(RedisMachineStore.MACHINES_KEY) is None

    store = RedisMachineStore(redis_conn=my_redisdb)
    store.get(SHA256("1"))
    store.find(name="not there")

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
    assert store.get(get_uuid(machine=machine)) == machine


def test_redis_machine_store_can_delete(logfix, my_redisdb, machine_factory):
    """Test the RedisMachineStore can delete a machine from the store."""

    store = RedisMachineStore(redis_conn=my_redisdb)
    machine = machine_factory()
    uuid = get_uuid(machine=machine)
    store.put(machine)
    assert store.get(uuid) == machine
    store.delete(uuid)
    assert store.get(uuid) is None


def test_redis_machine_store_raises_value_on_deleting_missing_machine(
    logfix, my_redisdb, machine_factory
):
    """Test RedisMachineStore raises ValueError deleting missing machine."""

    store = RedisMachineStore(redis_conn=my_redisdb)
    machine = machine_factory()
    with pytest.raises(ValueError):
        store.delete(get_uuid(machine=machine))


def test_redis_machine_store_can_find_machines_by_attr(
    logfix, my_redisdb, machine_factory
):
    """Test the RedisMachineStore can find machines by matching attrs."""

    store = RedisMachineStore(redis_conn=my_redisdb)
    machines = [machine_factory(provision=True) for _ in range(5)]
    uuids = {get_uuid(machine=machine) for machine in machines}
    for machine in machines:
        store.put(machine)

    assert (
        set(map(lambda m: get_uuid(machine=m), store.find(provision=True)))
        == uuids
    )
    assert store.find(provision=False) == set()


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

    # find collisions on uuids
    machine_all_dict = {}
    for machine in machine_all:
        machine_all_dict[get_uuid(machine=machine)] = machine
    machine_all = list(machine_all_dict.values())

    tuple(map(store.put, machine_all))

    assert store.all() == set(machine_all)
    assert store.find(provision=True).issubset(set(machine_all))
