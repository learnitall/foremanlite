# -*- coding: utf-8 -*-
"""Representation of machine information."""
import json
import re
import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

Mac = t.NewType("Mac", str)


class Arch(Enum):
    """Represent architecture of a machine."""

    x86_64 = "x86_64"  # pylint: disable=invalid-name
    aarch64 = "aarch64"  # pylint: disable=invalid-name


@dataclass
class Machine:
    """Represent information about a pxe-booted machine."""

    name: str
    mac: Mac
    arch: Arch

    def __eq__(self, other) -> bool:
        return repr(self) == repr(other)

    def __hash__(self):
        return hash(repr(self))


class MachineSelector(ABC):
    """Base Machine Selector class."""

    @abstractmethod
    def matches(self, machine: Machine) -> bool:
        """Return if the given machine matches the selector."""


class ExactMachineSelector(MachineSelector):
    """
    ExactMachineSelector matches machines based on expected attribute values.

    Parameters
    ----------
    val : str
        Value to match against.
    attr : str
        Attribute of Machine to match val against.

    Examples
    --------
    >>> from foremanlite.machine import *
    >>> machine = Machine(name="test", mac="11:22:33:44", arch=Arch.aarch64)
    >>> selector = ExactMachineSelector(attr="mac", val="11:22:33:44")
    >>> selector.matches(machine)
    True
    >>> selector = ExactMachineSelector(attr="name", val="test2")
    >>> selector.matches(machine)
    False
    """

    def __init__(self, val: str, attr: str):
        self.val: str = val
        self.attr: str = attr

    def matches(self, machine: Machine) -> bool:
        attr = getattr(machine, self.attr, None)
        if attr is None:
            return False

        return attr == self.val


class RegexMachineSelector(MachineSelector):
    """
    RegexMachineSelector matches Machines based on regex strings.

    Match must be exact (i.e. from beginning of string).
    Regex search will not be performed.

    Parameters
    ----------
    val : str
        Regex string to match against.
    attr : str
        Attribute of Machine to match regex string against.

    Examples
    --------
    >>> from foremanlite.machine import *
    >>> machine = Machine(name="test", mac="11:22:33:44", arch=Arch.aarch64)
    >>> selector = RegexMachineSelector(attr="mac", val="^11:22:.*$")
    >>> selector.matches(machine)
    True
    >>> selector = ExactMachineSelector(attr="name", val="est")
    >>> selector.matches(machine)
    False
    """

    def __init__(self, val: str, attr: str):
        self.reg: str = val
        self.attr: str = attr

    def matches(self, machine: Machine) -> bool:
        """
        Determine if this selector matches the given matchine.

        Parameters
        ----------
        machine : Machine
            Machine to determine if selection matches

        Returns
        -------
        bool
        """

        attr = getattr(machine, self.attr, None)
        if attr is None:
            return False

        return re.match(self.reg, attr) is not None


class MachineGroup:
    """
    Representation of a group of machines.

    Uses Selectors to match machines to the group.

    Only one of the given selectors needs to match a Machine
    for it to be considered in this group.

    Parameters
    ----------
    name : str
        Name representing this machine group
    selectors : list of MachineSelector
        MachineSelectors that describe this group.
    group_vars : dict
        Variables to associate with this group.
    """

    SELECTORS = {
        "exact": ExactMachineSelector,
        "regex": RegexMachineSelector,
    }

    def __init__(
        self,
        name: str,
        selectors: t.Iterable[MachineSelector],
        group_vars: t.Optional[t.Dict[str, t.Any]] = None,
    ):
        self.name = name
        self.selectors = selectors
        self.machines: t.Set[Machine] = set()
        self.vars = group_vars

    def matches(self, machine: Machine) -> bool:
        """Return if the given machine belongs to this group."""

        for selector in self.selectors:
            if selector.matches(machine):
                return True

        return False

    def filter(self, machines: t.Iterable[Machine]) -> int:
        """
        Filter the given iterable of Machines.

        Add the Machines which belong to this group into the 'machines'
        attribute.

        Parameters
        ----------
        machines : iterable of Machine
            iterable of Machine instance to filter into this group.

        Returns
        -------
        int
            Number of machines from the given iterable that were matched
            into the group.
        """

        count = 0
        for machine in machines:
            if self.matches(machine):
                self.machines.add(machine)
                count += 1

        return count

    @classmethod
    def from_json(cls, json_str: str) -> "MachineGroup":
        """
        Parse a MachineGroup from the given json string.

        Expected format:

        ```
        {
            "name": name,
            "selectors": [
                {
                    "type": type,
                    attr: val,
                },
                ...
            ],
            "vars": {
                var1: value1,
                ...
            }
        }
        ```

        Parameters
        ----------
        json : str
            json to parse into a MachineGroup instance.

        Raises
        ------
        ValueError
            if the config could not be parsed correctly

        Examples
        --------
        >>> import json
        >>> from foremanlite.machine import *
        >>> config = {
        ...     "name": "test",
        ...     "selectors": [{
        ...         "type": "exact",
        ...         "val": "mymachine",
        ...         "attr": "name"
        ...     }],
        ...     "vars": {
        ...         "yougood?": True
        ...     }
        ... }
        >>> mg = MachineGroup.from_json(json.dumps(config))
        >>> machine = Machine(name="mymachine", mac=None, arch=None)
        >>> mg.filter([machine])
        1
        >>> list(mg.machines)[0].name
        'mymachine'
        >>> mg.vars["yougood?"]
        True
        """

        config = json.loads(json_str)
        name, selectors = config.get("name", None), config.get(
            "selectors", None
        )

        if name is None or selectors is None:
            raise ValueError(
                "Expected name and selectors keys, one of them is missing."
            )

        selector_instances = []
        for selector in selectors:
            sel_type = selector.get("type", None)
            if sel_type is None:
                raise ValueError(
                    "Expected type attribute in selector but it is missing: "
                    f"{selector}"
                )

            sel_cls = cls.SELECTORS.get(sel_type.lower(), None)
            if sel_cls is None:
                raise ValueError(
                    f"Could not find selector with name {sel_type}"
                )

            del selector["type"]
            try:
                selector_instances.append(sel_cls(**selector))
            except Exception as err:
                raise ValueError(
                    f"Unable to create selector {sel_type}: {err}"
                )

        return cls(
            name=name,
            selectors=selector_instances,
            group_vars=config.get("vars", None),
        )
