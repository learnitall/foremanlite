#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test components of foremanlite.machine

The tests in here are pretty basic and non-exhaustive.
Could use more work to get truly full coverage.
"""
import json

import pytest

from foremanlite.machine import (
    Arch,
    Mac,
    Machine,
    MachineGroup,
    MachineSelector,
    _filter_groups,
)


def test_exact_machine_selector_matches_attributes_exactly():
    """Test xxact MachineSelector matches Machines by exact attributes."""

    machine = Machine(
        name="test", mac=Mac("11:22:33:44:55:66"), arch=Arch.aarch64
    )
    selector = MachineSelector(
        type="exact", attr="mac", val="11:22:33:44:55:66"
    )
    assert selector.matches(machine)
    selector = MachineSelector(type="exact", attr="name", val="test2")
    assert not selector.matches(machine)


def test_regex_machine_selector_matches_attributes_with_regex_str():
    """Test RegexMachineSelector matches Machines with regex strs."""

    machine = Machine(
        name="test", mac=Mac("11:22:33:44:55:66"), arch=Arch.aarch64
    )
    selector = MachineSelector(type="regex", attr="mac", val="^11:22:.*$")
    assert selector.matches(machine)
    selector = MachineSelector(type="regex", attr="name", val="est")
    assert not selector.matches(machine)


def test_machine_group_from_json_can_parse_json_into_machine_group_instance():
    """ "Test MachineGroup.from_json parses json string."""

    config = {
        "name": "test",
        "selectors": [{"type": "exact", "val": "mymachine", "attr": "name"}],
        "vars": {"yougood?": True},
    }
    group = MachineGroup.parse_raw(json.dumps(config))
    machine = Machine(name="mymachine", mac=Mac(""), arch=Arch.aarch64)
    assert group.filter([machine]) == 1
    assert list(group.machines)[0].name == "mymachine"
    assert group.vars is not None and group.vars["yougood?"]


def test_machine_group_from_json_raises_value_error_on_parse_error():
    """Test MachineGroup.from_json raises `ValueError` on bad json."""

    bad_config = {"name": "test"}  # missing selectors
    with pytest.raises(ValueError):
        MachineGroup.parse_raw(json.dumps(bad_config))


def test_filter_groups_returns_correct_set_of_group_membership():
    """Test filter_groups returns the groups a machine is a part of."""

    machine = Machine(
        name="test", mac=Mac("11:22:33:44:55:66"), arch=Arch.x86_64
    )
    groups = {
        MachineGroup(
            name="name is test",
            selectors=[MachineSelector(type="exact", attr="name", val="test")],
        ),
        MachineGroup(
            name="name is tset",
            selectors=[MachineSelector(type="exact", attr="name", val="tset")],
        ),
    }

    matches = _filter_groups(machine, tuple(groups))
    assert len(matches) == 1
    assert matches.pop().name == "name is test"
