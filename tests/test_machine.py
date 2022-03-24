#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test components of foremanlite.machine

The tests in here are pretty basic and non-exhaustive.
Could use more work to get truly full coverage.
"""
import re
import typing as t

import pytest
from hypothesis import given
from hypothesis import strategies as st

from foremanlite.machine import (
    Arch,
    Mac,
    Machine,
    MachineGroup,
    MachineGroupSet,
    MachineSelector,
    SelectorMatchStr,
    get_uuid,
)

from .conftest import machine_strategy, two_unique_machines_strategy


class TestMachine:
    """Test functionality of foremanlite.machine.Machine"""

    @staticmethod
    @given(st.sampled_from([a.value for a in Arch]))
    def test_str_arch_gets_cased_to_enum(arch_str: str):
        """Test the Arch attr gets casted to enum, even if str given."""

        assert isinstance(arch_str, str)  # quick sanity check
        machine = Machine(
            name="name",
            mac=Mac("mac"),
            provision=True,
            arch=arch_str,
        )
        assert isinstance(machine.arch, Arch)
        assert machine.arch.value == arch_str
        assert machine.arch == Arch(arch_str)

    @staticmethod
    @given(two_unique_machines_strategy())
    def test_hash_is_different_for_two_different_machines(
        machines: t.Tuple[Machine, Machine]
    ):
        """Test the hash of a machine is unique to all its attrs."""

        machine_one, machine_two = machines
        assert hash(machine_one) != hash(machine_two)
        for key, value in machine_one.dict().items():
            setattr(machine_two, key, value)
        assert hash(machine_one) == hash(machine_two)

    @staticmethod
    @given(two_unique_machines_strategy())
    def test_hash_is_different_than_uuid(machines: t.Tuple[Machine, Machine]):
        """
        Test that the hash of a machine is distinct from its uuid.

        uuid is based off of mac and arch only, hash is based off of
        all attributes.
        """

        machine_one, machine_two = machines
        hash_one = hash(machine_one)
        uuid_one = get_uuid(machine=machine_one)
        machine_one.provision = machine_two.provision
        machine_one.name = machine_two.name

        assert hash(machine_one) != hash_one
        assert get_uuid(machine=machine_one) == uuid_one


class TestGetUUID:
    """Test functionality of foremanlite.machine.get_uuid"""

    @staticmethod
    @given(machine_strategy())
    def test_get_uuid_returns_same_if_machine_or_arch_and_mac(
        machine: Machine,
    ):
        """Test get_uuid returns same uuid for all kwarg options."""

        assert get_uuid(machine=machine) == get_uuid(
            mac=machine.mac, arch=machine.arch
        )

    @staticmethod
    @given(two_unique_machines_strategy())
    def test_get_uuid_keys_off_of_arch_and_mac(
        machines: t.Tuple[Machine, Machine]
    ):
        """Test get_uuid returns same uuid for same arch and mac."""

        machine_one, machine_two = machines
        assert get_uuid(machine=machine_one) != get_uuid(machine=machine_two)
        machine_two.arch = machine_one.arch
        machine_two.mac = machine_one.mac
        assert get_uuid(machine=machine_one) == get_uuid(machine=machine_two)


class TestMachineSelector:
    """Test functionality of foremanlite.machine.MachineSelector."""

    @staticmethod
    @given(two_unique_machines_strategy())
    def test_exact_machine_selector_matches_attributes_exactly(
        machines: t.Tuple[Machine, Machine]
    ):
        """Test exact MachineSelector matches Machines by exact attributes."""

        machine_one, machine_two = machines
        for key, value in machine_one.dict().items():
            selector = MachineSelector(type="exact", attr=key, val=value)
            assert selector.matches(machine_one)
            assert not selector.matches(machine_two)

    @staticmethod
    @given(two_unique_machines_strategy())
    def test_regex_machine_selector_matches_attributes_with_regex_str(
        machines: t.Tuple[Machine, Machine]
    ):
        """Test regex MachineSelector matches Machines with regex strings."""

        machine_one, machine_two = machines
        for key, value in machine_one.dict().items():
            if isinstance(value, Arch):
                value = value.value
            value = str(value)
            selector = MachineSelector(
                type="regex", attr=key, val=f"^{re.escape(value)}$"
            )
            assert selector.matches(machine_one)
            assert not selector.matches(machine_two)


class TestSelectorMatchStr:
    """Test functionality of foremanlite.machine.SelectorMatchStr."""

    @staticmethod
    @given(st.text(alphabet=st.characters(blacklist_characters=["{", "}"])))
    def test_test_method_raises_value_error_on_bad_template_output(
        bad_jinja_str: str,
    ):
        """Check that test raises ValueError on bad template output."""

        with pytest.raises(ValueError):
            assert SelectorMatchStr(exp=bad_jinja_str).test({})

    @staticmethod
    @given(st.booleans())
    def test_test_method_is_not_case_sensitive(bool_val: bool):
        """Check that test is not case sensitive to expected boolean output"""

        bool_val_str = str(bool_val)
        checks = [
            bool_val_str.upper(),
            bool_val_str.capitalize(),
            bool_val_str.lower(),
            bool_val_str.swapcase(),
        ]
        for check in checks:
            assert SelectorMatchStr(exp=check).test({}) == bool_val

    @staticmethod
    @given(st.from_regex(re.compile(r"^\s*\{\}\s*$")))
    def test_test_method_is_not_sensitive_to_whitespace(bool_val_str: str):
        """Check that test is not sensitive to whitespace surrounding output"""

        for expected in [True, False]:
            exp = bool_val_str.format(str(expected))
            assert SelectorMatchStr(exp=exp).test({}) == expected

    @staticmethod
    @given(
        bool_vals=st.lists(st.booleans(), min_size=4, max_size=4),
        machines=two_unique_machines_strategy(),
    )
    def test_test_method_can_substitute_in_names_and_eval_exp(
        bool_vals: t.List[bool],
        machines: t.Tuple[Machine, Machine],
        monkeypatch,
    ):
        """Check that test can substitute selector results into an exp."""

        # Don't know how to dynamically generate these,
        # so just use a hardcoded one
        exp = (
            "{% if (name and provision) or arch or mac %} true "
            "{% else %} false {% endif %}"
        )
        selector_results = dict(
            zip(["name", "provision", "arch", "mac"], bool_vals)
        )

        def mock_test(_, selector_values: t.Dict[str, bool]):
            """Mock test method to check expected input"""
            assert selector_values == selector_results

        monkeypatch.setattr(SelectorMatchStr, "test", mock_test)

        selectors = []
        machine_one, machine_two = machines
        for selector_name, bool_val in selector_results.items():
            selector = MachineSelector(
                type="exact",
                name=selector_name,
                attr=selector_name,
                val=getattr(
                    machine_one if bool_val else machine_two, selector_name
                ),
            )
            selectors.append(selector)

        SelectorMatchStr(exp=exp).apply(machine_one, selectors)


class TestMachineGroupSet:
    """Test functionality of foremanlite.machine.MachineGroupSet"""

    @staticmethod
    @given(two_unique_machines_strategy())
    def test_filter_returns_correct_set_of_group_membership(
        machines: t.Tuple[Machine, Machine]
    ):
        """Test filter returns the groups a machine is a part of."""

        machine_one, machine_two = machines
        machine_one_attrs = machine_one.dict().items()
        machine_two_attrs = machine_two.dict().items()
        both_attrs = [*machine_one_attrs, *machine_two_attrs]
        groups = [
            MachineGroup(
                name="group_one",
                selectors=[
                    MachineSelector(type="exact", attr=attr, val=val)
                    for attr, val in machine_one_attrs
                ],
            ),
            MachineGroup(
                name="group_two",
                selectors=[
                    MachineSelector(type="exact", attr=attr, val=val)
                    for attr, val in machine_two_attrs
                ],
            ),
            MachineGroup(
                name="group_three",
                selectors=[
                    MachineSelector(
                        name=str(i), type="exact", attr=attr, val=val
                    )
                    for i, (attr, val) in enumerate(both_attrs)
                ],
                # will not match since these are all and-ed together
                match_str=SelectorMatchStr(
                    exp="{% if "
                    + " and ".join(map(str, range(len(both_attrs))))
                    + "%} True {% else %} False {% endif %}"
                ),
            ),
        ]
        machine_group_set = MachineGroupSet(groups=groups)
        one_groups = machine_group_set.filter(machine_one)
        two_groups = machine_group_set.filter(machine_two)
        assert len(one_groups) == 1
        assert len(two_groups) == 1
        assert one_groups[0].name == "group_one"
        assert two_groups[0].name == "group_two"
