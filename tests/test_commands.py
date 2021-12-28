#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name,unused-argument
"""Test functionality of the foremanlite cli commands."""
import json
import time
from pathlib import Path

import click
import pytest

import foremanlite.logging
from foremanlite.cli.commands.groups import print_groups
from foremanlite.cli.commands.machines import print_machines
from foremanlite.cli.commands.provision import toggle_provision
from foremanlite.cli.config import Config
from foremanlite.machine import (
    Arch,
    ExactMachineSelector,
    MachineGroup,
    MachineGroupSet,
)
from foremanlite.serve.context import ServeContext
from foremanlite.store import RedisMachineStore
from foremanlite.vars import DATA_DIR, EXEC_DIR, GROUPS_DIR, STATIC_DIR


@pytest.fixture()
def clilogfix():
    """
    Teardown logging after each test.

    These commands will setup logging when given the `verbose=True`
    argument, therefore don't need to perform any setup tasks for
    logging.
    """

    yield
    foremanlite.logging.teardown()


def test_toggle_provision_quits_with_no_store(clilogfix, monkeypatch):
    """Test toggle_provision quits when no store is configured."""

    def mockecho(msg: str):
        """Assert given message contains 'no store configured'"""
        assert "no store configured" in msg.lower()

    monkeypatch.setattr(click, "echo", mockecho)

    config = Config(
        verbose=True,
        redis=False,
    )
    toggle_provision(config)


def test_toggle_provision_quits_when_cannot_find_machine(
    clilogfix, monkeypatch, my_redisdb
):
    """Test toggle_provision quits when no machine could be found."""

    def mockecho(msg: str):
        """Assert given message contains 'could not find given machine'"""
        assert "could not find given machine" in msg.lower()

    def mock_get_store(*args, **kwargs):
        """Mock ServeContext.get_store to return the mocked redis instance."""
        return RedisMachineStore(redis_conn=my_redisdb)

    monkeypatch.setattr(click, "echo", mockecho)
    monkeypatch.setattr(ServeContext, "get_store", mock_get_store)

    config = Config(
        verbose=True,
        redis=True,
    )
    toggle_provision(config, mac="not a mac")


def test_toggle_provision_quits_when_more_than_one_machine_is_found(
    clilogfix, monkeypatch, my_redisdb, unique_machine_factory
):
    """Test toggle_provision quits when more than one machine is found."""

    def mockecho(msg: str):
        """Assert given message contains 'more than one machine'"""
        assert "more than one machine" in msg.lower()

    store = RedisMachineStore(redis_conn=my_redisdb)
    machines = unique_machine_factory(3)
    for machine in machines:
        machine.name = "my_machine"
        store.put(machine)

    def mock_get_store(*args, **kwargs):
        """Mock ServeContext.get_store to return the mocked redis instance."""
        return store

    monkeypatch.setattr(click, "echo", mockecho)
    monkeypatch.setattr(ServeContext, "get_store", mock_get_store)

    config = Config(
        verbose=True,
        redis=True,
    )

    toggle_provision(config, name="my_machine")


def test_toggle_provision_actually_toggles_provision(
    clilogfix, monkeypatch, my_redisdb, unique_machine_factory
):
    """Test toggle_provision actually toggles the provision attribute."""

    msgs = [
        "provision attribute is none",
        "setting provision attribute to false",
        "setting provision attribute to true",
    ]

    def mockecho(msg: str):
        """Assert given message contains messages in msg queue."""
        # this one comes before the msgs in msgs
        if "found machine described" in msg.lower():
            return
        assert msgs.pop(0) in msg.lower()

    store = RedisMachineStore(redis_conn=my_redisdb)

    # ensure our machines are unique
    machines = unique_machine_factory(3)
    machines[0].name = "my_test_machine_toggle"
    machines[0].provision = None
    for machine in machines:
        store.put(machine)

    def mock_get_store(*args, **kwargs):
        """Mock ServeContext.get_store to return the mocked redis instance."""
        return store

    monkeypatch.setattr(click, "echo", mockecho)
    monkeypatch.setattr(ServeContext, "get_store", mock_get_store)

    config = Config(
        verbose=True,
        redis=True,
    )

    time.sleep(0.1)  # let things settle

    for _ in range(3):
        toggle_provision(config, name="my_test_machine_toggle")


@pytest.fixture()
def setup_mock_config(unique_machine_factory, my_redisdb, tmpdir, monkeypatch):
    """
    Setup a list of groups and machines and return a ready-to-go config.

    This is used to help create tests for print_machines
    """

    store = RedisMachineStore(redis_conn=my_redisdb)

    # ensure our machines are unique
    machines = unique_machine_factory(3)
    machines[0].name = "machine_group_1"
    machines[1].name = "machine_group_2_1"
    machines[2].name = "machine_group_2_2"
    for machine in machines:
        store.put(machine)

    def mock_get_store(*args, **kwargs):
        """Mock ServeContext.get_store to return the mocked redis instance."""
        return store

    monkeypatch.setattr(ServeContext, "get_store", mock_get_store)

    config_dir = Path(tmpdir)
    groups = [
        {
            "name": "group1",
            "selectors": [
                {"type": "exact", "attr": "name", "val": "machine_group_1"}
            ],
            "vars": {"var": "one"},
        },
        {
            "name": "group2",
            "selectors": [
                {
                    "type": "regex",
                    "attr": "name",
                    "val": "machine_group_2_[12]",
                },
            ],
            "vars": {"var": "two", "another": "var"},
        },
        {
            "name": "group3",
            "selectors": [
                {"type": "exact", "attr": "name", "val": "machine_group_2_2"},
            ],
            "vars": {
                "var": "three",
            },
        },
    ]
    for directory in (DATA_DIR, EXEC_DIR, GROUPS_DIR, STATIC_DIR):
        (config_dir / directory).mkdir()
    for i, group in enumerate(groups):
        (config_dir / GROUPS_DIR / f"groups_{i}.json").write_text(
            json.dumps(group)
        )

    return Config(verbose=True, redis=True, config_dir=str(config_dir))


def test_print_machines_quits_if_no_store_is_configured(
    clilogfix, monkeypatch
):
    """Test print_machines quits if not store is configured."""

    def mockecho(msg: str):
        """Assert given message contains 'no store configured'"""
        assert "no store configured" in msg.lower()

    monkeypatch.setattr(click, "echo", mockecho)

    config = Config(
        verbose=True,
        redis=False,
    )
    print_machines(config)


def test_print_machines_prints_all_machines_if_no_filters_given(
    clilogfix, monkeypatch, setup_mock_config
):
    """
    Test print_machines will print all machines if no filters given.

    Heavily coupled with data in the setup_mock_config fixture.
    """

    def mockecho(msg):
        """Assert given table contains 3 rows."""
        if isinstance(msg, str):
            return
        assert len(msg.rows) == 3

    monkeypatch.setattr(click, "echo", mockecho)
    config: Config = setup_mock_config

    time.sleep(0.1)  # let things settle
    print_machines(config)


def test_print_machines_filters_machines_if_filters_given(
    clilogfix, monkeypatch, setup_mock_config
):
    """
    Test print_machines will only print subset if filters are given.

    Heavily coupled with data in the setup_mock_config fixture.
    """

    def mockecho(msg):
        """Assert given table instance contains only one machine."""
        if isinstance(msg, str):
            return
        assert len(msg.rows) == 1
        # row[0] contains the machine's name
        assert any(("machine_group_2_1" == row[0]) for row in msg.rows)
        assert any(("machine_group_2_2" != row[0]) for row in msg.rows)
        assert all(("machine_group_1" != row[0]) for row in msg.rows)

    monkeypatch.setattr(click, "echo", mockecho)
    config: Config = setup_mock_config

    time.sleep(0.1)
    print_machines(config, name="machine_group_2_1")


def test_print_machines_prints_groups_and_group_vars(
    clilogfix, monkeypatch, setup_mock_config
):
    """
    Test print_machines will show machine group's as well as group vars.

    Heavily coupled with data in the setup_mock_config fixture.
    """

    def mockecho(msg):
        """Assert the right groups and group vars are given."""
        if isinstance(msg, str):
            return
        assert len(msg.rows) == 3
        for row in msg.rows:
            # row[0] contains the name
            # row[4] contains group name
            # row[5] contains vars
            if row[0] == "machine_group_1":
                assert row[4] == "group1"
                assert row[5] == "var=one"
            elif row[0] == "machine_group_2_1":
                assert row[4] == "group2"
                assert row[5] == "var=two, another=var"
            elif row[0] == "machine_group_2_2":
                assert row[4] == "group2, group3"
                assert row[5] == "var=three, another=var"
            else:
                assert False

    monkeypatch.setattr(click, "echo", mockecho)
    config: Config = setup_mock_config
    time.sleep(0.1)
    print_machines(config)


def test_print_groups_prints_group_set_json(clilogfix, tmpdir, monkeypatch):
    """Test print_groups prints all groups as json."""

    group_set = MachineGroupSet(
        groups={
            MachineGroup(
                name="group1",
                selectors=[ExactMachineSelector(attr="name", val="machine1")],
            ),
            MachineGroup(
                name="group2",
                selectors=[ExactMachineSelector(attr="mac", val="not a mac")],
                group_vars={"a": "b"},
            ),
            MachineGroup(
                name="group3",
                selectors=[
                    ExactMachineSelector(attr="arch", val=Arch.aarch64.value),
                    ExactMachineSelector(attr="provision", val=str(True)),
                ],
                group_vars={"my_group_var": "a_group_var_value"},
            ),
        }
    )

    def mockecho(msg):
        """Assert given string is equal to the configured group set."""

        group_set_json = json.loads(group_set.to_json())
        for group in json.loads(msg):
            assert group in group_set_json

    monkeypatch.setattr(click, "echo", mockecho)

    config_dir = Path(tmpdir)
    for directory in (DATA_DIR, EXEC_DIR, GROUPS_DIR, STATIC_DIR):
        (config_dir / directory).mkdir()
    for i, group in enumerate(group_set.all()):
        (config_dir / GROUPS_DIR / f"groups_{i}.json").write_text(
            group.to_json()
        )

    print_groups(Config(verbose=True, redis=False, config_dir=str(config_dir)))
