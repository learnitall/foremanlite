#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=redefined-outer-name,unused-argument
"""Test functionality of the foremanlite cli commands."""
import json
import random
import time
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

import click
import pytest
from hypothesis import given
from hypothesis import strategies as st

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
    Machine,
    MachineGroup,
    MachineGroupSet,
    MachineSelector,
    get_uuid,
)
from foremanlite.serve.context import ServeContext
from foremanlite.store import BaseMachineStore, RedisMachineStore
from foremanlite.vars import DATA_DIR, EXEC_DIR, GROUPS_DIR, STATIC_DIR

from .conftest import machine_strategy, two_unique_machines_strategy

pytestmark = pytest.mark.usefixtures("do_log_teardown")


@dataclass
class MockConfig:
    """Hold resources for mocking runtime config"""

    machines: t.List[Machine] = field(default_factory=list)
    groups: MachineGroupSet = MachineGroupSet(groups=[])
    store: t.Optional[BaseMachineStore] = None
    config: t.Optional[Config] = None
    config_dir: t.Optional[Path] = None


@st.composite
def config_strategy(draw):
    """Hypothesis strategy to generate runtime config."""

    machines = draw(
        st.lists(
            machine_strategy(),
            unique_by=lambda machine: get_uuid(machine=machine),
            min_size=3,
        )
    )
    pull_attr = lambda attr: [
        getattr(m, attr) if attr != "arch" else getattr(m, attr).value
        for m in machines
    ]

    possible_selectors = list(
        {
            (attr, value)
            for attr in ["arch", "mac", "provision", "name"]
            for value in pull_attr(attr)
        }
    )
    chosen_selector_args = draw(
        st.lists(st.sampled_from(possible_selectors), unique=True, min_size=1)
    )
    selectors = [
        MachineSelector(type="exact", attr=args[0], val=args[1])
        for args in chosen_selector_args
    ]
    selector_strategy = st.sampled_from(selectors)

    groups = draw(
        st.lists(
            st.builds(
                MachineGroup,
                name=st.text(min_size=1),
                vars=st.dictionaries(
                    keys=st.text(min_size=1),
                    values=st.text(min_size=1),
                ),
                selectors=st.lists(selector_strategy, min_size=1),
                match_str=st.none(),
            )
        )
    )
    return MockConfig(machines=machines, groups=MachineGroupSet(groups=groups))


@pytest.fixture()
def setup_mock_config(my_redisdb, contentdir_factory, monkeypatch):
    """Setup factory for establishing mock runtime config"""

    def _setup(mock_config: t.Optional[MockConfig] = None):
        # anything that uses hypothesis testing needs to do these
        # two steps, as fixtures won't be called until all
        # examples have finished
        my_redisdb.flushall(asynchronous=False)
        foremanlite.logging.teardown()

        store = RedisMachineStore(redis_conn=my_redisdb)

        def mock_get_store(*args, **kwargs):
            """Mock get_store to return the mocked redis instance."""
            return store

        monkeypatch.setattr(ServeContext, "get_store", mock_get_store)

        config_dir = contentdir_factory()
        for directory in (DATA_DIR, EXEC_DIR, GROUPS_DIR, STATIC_DIR):
            (config_dir / directory).mkdir()

        if mock_config is not None:
            for machine in mock_config.machines:
                store.put(machine)
            for i, group in enumerate(mock_config.groups.all()):
                (config_dir / GROUPS_DIR / f"groups_{i}.json").write_text(
                    group.json()
                )
        else:
            mock_config = MockConfig()

        mock_config.store = store
        mock_config.config_dir = config_dir
        mock_config.config = Config(
            verbose=True, redis=True, config_dir=str(config_dir)
        )

        return mock_config

    return _setup


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

        config: Config = setup_mock_config().config
        for mac, arch in [("here", None), (None, "here"), (None, None)]:
            func(config, mac=mac, arch=arch, **kwargs)

    return _do_test


class TestPrintMachines:
    """Test foremanlite.cli.commands.machines.print_machines"""

    @staticmethod
    def test_print_machine_quits_with_no_store(test_no_store_configured):
        """Test print_machine quits when no store is configured."""

        test_no_store_configured(print_machines)

    @staticmethod
    @given(mock_config=config_strategy())
    def test_print_machines_prints_all_machines_if_no_filters_given(
        mock_config, monkeypatch, setup_mock_config
    ):
        """
        Test print_machines will print all machines if no filters given.
        """

        setup_mock_config(mock_config)

        def mockecho(msg):
            """Assert given table contains a row for each machine."""
            if isinstance(msg, str):
                return
            assert len(msg.rows) == len(mock_config.machines)

        monkeypatch.setattr(click, "echo", mockecho)
        config: Config = mock_config.config

        time.sleep(0.1)  # let things settle
        print_machines(config)

    @staticmethod
    @given(mock_config=config_strategy())
    def test_print_machines_filters_machines_if_filters_given(
        mock_config, monkeypatch, setup_mock_config
    ):
        """
        Test print_machines will only print subset if filters are given.

        Heavily coupled with data in the setup_mock_config fixture.
        """

        setup_mock_config(mock_config)
        chosen_machine = random.choice(mock_config.machines)

        def mockecho(msg):
            """Assert given table instance contains only one machine."""
            if isinstance(msg, str):
                return
            assert len(msg.rows) == 1
            # row[0] contains the machine's name
            # row[1] ... mac
            # row[2] ... arch
            # row[3] ... provision
            assert msg.rows[0][0] == repr(chosen_machine.name)
            assert msg.rows[0][1] == repr(chosen_machine.mac)
            assert msg.rows[0][2] == repr(chosen_machine.arch.value)
            assert msg.rows[0][3] == repr(chosen_machine.provision)

        monkeypatch.setattr(click, "echo", mockecho)
        print_machines(mock_config.config, **chosen_machine.dict())

    @staticmethod
    @given(mock_config=config_strategy())
    def test_print_machines_prints_groups_and_group_vars(
        mock_config: MockConfig, monkeypatch, setup_mock_config
    ):
        """Test print_machines will show machine group's and vars."""

        setup_mock_config(mock_config)
        assert mock_config.config is not None

        def mockecho(msg):
            """Assert the right groups and group vars are given."""
            if isinstance(msg, str):
                return
            assert len(msg.rows) == len(mock_config.machines)
            for row in msg.rows:
                # row[0] contains the name
                # row[4] contains group name
                # row[5] contains vars
                found_machine = None
                for machine in mock_config.machines:
                    if (
                        repr(machine.name) == row[0]
                        and repr(machine.mac) == row[1]
                        and repr(machine.arch.value) == row[2]
                        and repr(machine.provision) == row[3]
                    ):
                        found_machine = machine
                        break

                assert found_machine is not None
                groups = mock_config.groups.filter(found_machine)
                for group in groups:
                    assert group.name in row[4]
                    if group.vars is not None:
                        for var_name, var_value in group.vars.items():
                            assert var_name in row[5]
                            assert var_value in row[5]

        monkeypatch.setattr(click, "echo", mockecho)
        print_machines(mock_config.config)


class TestAddMachine:
    """Test foremanlite.cli.commands.machines.add_machine."""

    @staticmethod
    def test_add_machine_quits_with_no_store(test_no_store_configured):
        """Test add_machine quits when no store is configured."""

        test_no_store_configured(add_machine)

    @staticmethod
    def test_add_machine_quits_with_no_mac_and_arch(test_no_mac_or_arch):
        """Test add_machine quits when both mac and arch aren't given."""

        test_no_mac_or_arch(add_machine)

    @staticmethod
    @given(machine=machine_strategy())
    def test_add_machine_adds_given_machine_to_store(
        machine, setup_mock_config
    ):
        """Test add_machine adds the given machine to the store."""

        mock_config: MockConfig = setup_mock_config()
        assert mock_config.config is not None
        assert mock_config.store is not None
        add_machine(mock_config.config, **machine.dict())
        assert mock_config.store.get(get_uuid(machine=machine)) == machine


class TestDeleteMachine:
    """Test foremanlite.cli.commands.machines.delete_machine"""

    @staticmethod
    def test_delete_machine_quits_no_store(test_no_store_configured):
        """Test delete_machine quits when no store is configured."""

        test_no_store_configured(delete_machine)

    @staticmethod
    def test_delete_machine_quits_with_no_mac_and_arch(test_no_mac_or_arch):
        """Test delete_machine quits when both mac and arch aren't given."""

        test_no_mac_or_arch(delete_machine)

    @staticmethod
    @given(mock_config=config_strategy())
    def test_delete_machine_can_delete_machine_from_store(
        mock_config: MockConfig, setup_mock_config
    ):
        """Test delete_machine can delete given machine from the store."""

        setup_mock_config(mock_config)
        assert mock_config.config is not None
        assert mock_config.store is not None
        for machine in mock_config.machines:
            delete_machine(mock_config.config, **machine.dict())
            assert mock_config.store.get(get_uuid(machine=machine)) is None


class TestUpdateMachine:
    """Test foremanlite.cli.commands.machines.update_machine"""

    @staticmethod
    def test_update_machine_quits_no_store(test_no_store_configured):
        """Test update_machine quits when no store is configured."""

        test_no_store_configured(update_machine)

    @staticmethod
    def test_update_machine_quits_with_no_mac_and_arch(test_no_mac_or_arch):
        """Test update_machine quits when both mac and arch aren't given."""

        test_no_mac_or_arch(update_machine)

    @staticmethod
    @given(machines=two_unique_machines_strategy())
    def test_update_machine_can_update_machine_in_the_store(
        machines: t.Tuple[Machine, Machine], setup_mock_config
    ):
        """Test update_machine can update a machine in the store."""

        machine_one, machine_two = machines
        machine_two.arch = machine_one.arch
        machine_two.mac = machine_one.mac

        mock_config: MockConfig = setup_mock_config()
        assert mock_config.config is not None
        assert mock_config.store is not None
        mock_config.store.put(machine_one)
        update_machine(mock_config.config, **machine_two.dict())
        assert (
            mock_config.store.get(get_uuid(machine=machine_two)) == machine_two
        )

    @staticmethod
    @given(machine=machine_strategy())
    def test_update_machine_returns_if_machine_not_found(
        machine: Machine, setup_mock_config, monkeypatch
    ):
        """Test update_machine will quit if given machine cannot be found."""

        mock_config: MockConfig = setup_mock_config()
        assert mock_config.config is not None

        def patch_echo(msg: str):
            """Assert that msg contains 'could not find given machine'"""

            assert "could not find given machine" in msg.lower()

        monkeypatch.setattr(click, "echo", patch_echo)
        update_machine(mock_config.config, **machine.dict())


class TestPrintGroups:
    """Test foremanlite.cli.commands.groups.print_groups"""

    @staticmethod
    def test_print_groups_prints_group_set_json(tmpdir, monkeypatch):
        """Test print_groups prints all groups as json."""

        group_set = MachineGroupSet(
            groups=[
                MachineGroup(
                    name="group1",
                    selectors=[
                        MachineSelector(
                            type="exact", attr="name", val="machine1"
                        )
                    ],
                ),
                MachineGroup(
                    name="group2",
                    selectors=[
                        MachineSelector(
                            type="exact", attr="mac", val="not a mac"
                        )
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
            (config_dir / GROUPS_DIR / f"groups_{i}.json").write_text(
                group.json()
            )

        print_groups(
            Config(verbose=True, redis=False, config_dir=str(config_dir))
        )
