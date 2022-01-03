#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=unused-argument, redefined-outer-name
"""Test functionality in formanlite.store module."""
import typing as t

import pytest
from hypothesis import given
from hypothesis import strategies as st
from redis import Redis

from foremanlite.machine import SHA256, Machine, get_uuid
from foremanlite.store import RedisMachineStore

from .conftest import machine_strategy

pytestmark = pytest.mark.usefixtures("logfix")


class TestRedisMachineStore:
    """Test functionality of foremanlite.store.RedisMachineStore"""

    @staticmethod
    def test_redis_machine_store_does_not_fail_with_empty_db(
        my_redisdb, machine_factory
    ):
        """Test RedisMachineStore can handle working with an empty database."""

        assert my_redisdb.get(RedisMachineStore.MACHINES_KEY) is None

        store = RedisMachineStore(redis_conn=my_redisdb)
        store.get(SHA256("1"))
        store.find(name="not there")

        machine = machine_factory()
        store.put(machine)

    @staticmethod
    @given(machine=machine_strategy())
    def test_redis_machine_store_can_put_and_get(
        machine: Machine, my_redisdb: Redis
    ):
        """Test the RedisMachineStore can put and get on a new db."""

        store = RedisMachineStore(redis_conn=my_redisdb)
        store.put(machine)

        assert my_redisdb.get(store.MACHINES_KEY) is not None
        assert store.get(get_uuid(machine=machine)) == machine

    @staticmethod
    @given(machine=machine_strategy())
    def test_redis_machine_store_can_delete(
        machine: Machine, my_redisdb: Redis
    ):
        """Test the RedisMachineStore can delete a machine from the store."""

        store = RedisMachineStore(redis_conn=my_redisdb)
        uuid = get_uuid(machine=machine)
        store.put(machine)
        assert store.get(uuid) == machine
        store.delete(uuid)
        assert store.get(uuid) is None

    @staticmethod
    @given(machine=machine_strategy())
    def test_redis_machine_store_raises_value_on_deleting_missing_machine(
        machine: Machine, my_redisdb: Redis
    ):
        """Test RedisMachineStore raises ValueError deleting missing machine"""

        store = RedisMachineStore(redis_conn=my_redisdb)
        with pytest.raises(ValueError):
            store.delete(get_uuid(machine=machine))

    @staticmethod
    @given(
        machines=st.lists(
            machine_strategy(),
            unique_by=lambda machine: get_uuid(machine=machine),
        )
    )
    def test_redis_machine_store_can_find_machines_by_attr(
        machines: t.List[Machine], my_redisdb: Redis
    ):
        """Test the RedisMachineStore can find machines by matching attrs."""

        # my_redisdb is function scoped, so need to reset at end of test
        # in order to use hypothesis
        my_redisdb.flushall(asynchronous=False)
        store = RedisMachineStore(redis_conn=my_redisdb)
        results: t.Dict[str, t.Dict[t.Any, t.Set[Machine]]] = {}
        for machine in machines:
            store.put(machine)
            for attr, value in machine.dict().items():
                attrs: t.Optional[t.Dict[t.Any, t.Set[Machine]]] = results.get(
                    attr, None
                )
                if attrs is None:
                    attrs = {}
                    results[attr] = attrs
                machine_results: t.Optional[t.Set[Machine]] = attrs.get(
                    value, None
                )
                if machine_results is None:
                    machine_results = set()
                machine_results.add(machine)
                results[attr][value] = machine_results

        for attr, values in results.items():
            for value, machine_results in values.items():
                assert store.find(**{attr: value}) == machine_results

    @staticmethod
    @given(
        machines=st.lists(
            machine_strategy(),
            unique_by=lambda machine: get_uuid(machine=machine),
        )
    )
    def test_redis_machine_store_can_list_all_machines(
        machines: t.List[Machine], my_redisdb: Redis
    ):
        """Test the RedisMachineStore can return all machines in the store."""

        # my_redisdb is function scoped, so need to reset at end of test
        # in order to use hypothesis
        my_redisdb.flushall()
        store = RedisMachineStore(redis_conn=my_redisdb)
        for machine in machines:
            store.put(machine)

        assert store.all() == set(machines)
