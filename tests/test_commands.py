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
from foremanlite.cli.commands.machines import (
    add_machine,
    delete_machine,
    print_machines,
    update_machine,
)
from foremanlite.cli.config import Config
from foremanlite.machine import (
    Arch,
    Mac,
    Machine,
    MachineGroup,
    MachineGroupSet,
    MachineSelector,
    get_uuid,
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


@pytest.fixture()
def setup_mock_config(unique_machine_factory, my_redisdb, tmpdir, monkeypatch):
    """Setup a list of groups and machines and return a ready-to-go config."""

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


@pytest.fixture()
def test_no_store_configured(monkeypatch):
    """Test that commands give correct output when no store is configured."""

    def _do_test(func, **kwargs):
        def mockecho(msg: str):
            """Assert given message contains 'no store configured'"""
            assert "no store configured" in msg.lower()

        monkeypatch.setattr(click, "echo", mockecho)

        config = Config(
            verbose=True,
            redis=False,
        )

        func(config, **kwargs)

    return _do_test


@pytest.fixture()
def test_no_mac_or_arch(monkeypatch, setup_mock_config):
    """Test that commands give correct output when mac and arch are missing."""

    def _do_test(func, **kwargs):
        def mockecho(msg: str):
            """Assert given message contains 'need both a mac and arch'."""
            assert "need both a mac and arch" in msg.lower()

        monkeypatch.setattr(click, "echo", mockecho)

        config: Config = setup_mock_config
        for mac, arch in [("here", None), (None, "here"), (None, None)]:
            func(config, mac=mac, arch=arch, **kwargs)

    return _do_test


def test_print_machine_quits_with_no_store(
    clilogfix, test_no_store_configured
):
    """Test print_machine quits when no store is conifgured."""

    test_no_store_configured(print_machines)


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
        print(msg)
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


def test_add_machine_quits_with_no_store(clilogfix, test_no_store_configured):
    """Test add_machine quits when no store is configured."""

    test_no_store_configured(add_machine)


def test_add_machine_quits_with_no_mac_and_arch(
    clilogfix, test_no_mac_or_arch
):
    """Test add_machine quits when both mac and arch aren't given."""

    test_no_mac_or_arch(add_machine)


def test_add_machine_adds_given_machine_to_store(clilogfix, setup_mock_config):
    """Test add_machine adds the given machine to the store."""

    config: Config = setup_mock_config
    machine = Machine(
        mac=Mac("mac"), arch=Arch("x86_64"), name="my_machine", provision=True
    )

    as_dict = machine.dict()
    add_machine(config, **as_dict)
    store = ServeContext.get_store(config)
    assert store is not None
    assert store.get(get_uuid(machine=machine)) == machine


def test_delete_machine_quits_no_store(clilogfix, test_no_store_configured):
    """Test delete_machine quits when no store is configured."""

    test_no_store_configured(delete_machine)


def test_delete_machine_quits_with_no_mac_and_arch(
    clilogfix, test_no_mac_or_arch
):
    """Test delete_machine quits when both mac and arch aren't given."""

    test_no_mac_or_arch(delete_machine)


def test_update_machine_quits_no_store(clilogfix, test_no_store_configured):
    """Test update_machine quits when no store is configured."""

    test_no_store_configured(update_machine)


def test_update_machine_quits_with_no_mac_and_arch(
    clilogfix, test_no_mac_or_arch
):
    """Test update_machine quits when both mac and arch aren't given."""

    test_no_mac_or_arch(update_machine)


def test_print_groups_prints_group_set_json(clilogfix, tmpdir, monkeypatch):
    """Test print_groups prints all groups as json."""

    group_set = MachineGroupSet(
        groups=[
            MachineGroup(
                name="group1",
                selectors=[
                    MachineSelector(type="exact", attr="name", val="machine1")
                ],
            ),
            MachineGroup(
                name="group2",
                selectors=[
                    MachineSelector(type="exact", attr="mac", val="not a mac")
                ],
                vars={"a": "b"},
            ),
            MachineGroup(
                name="group3",
                selectors=[
                    MachineSelector(
                        type="exact", attr="arch", val=Arch.aarch64.value
                    ),
                    MachineSelector(
                        type="exact", attr="provision", val=str(True)
                    ),
                ],
                vars={"my_group_var": "a_group_var_value"},
            ),
        ]
    )

    def mockecho(msg):
        """Assert given string is equal to the configured group set."""

        group_set_json = group_set.dict()
        for group in json.loads(msg):
            assert group in group_set_json

    monkeypatch.setattr(click, "echo", mockecho)

    config_dir = Path(tmpdir)
    for directory in (DATA_DIR, EXEC_DIR, GROUPS_DIR, STATIC_DIR):
        (config_dir / directory).mkdir()
    for i, group in enumerate(group_set.all()):
        (config_dir / GROUPS_DIR / f"groups_{i}.json").write_text(group.json())

    print_groups(Config(verbose=True, redis=False, config_dir=str(config_dir)))
