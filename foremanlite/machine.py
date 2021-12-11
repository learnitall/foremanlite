# -*- coding: utf-8 -*-
"""Representation of machine information."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import NewType

Mac = NewType("Mac", int)


class Arch(Enum):
    """Represent architecture of a machine."""

    x86_64 = 1  # pylint: disable=invalid-name
    aarch64 = 2  # pylint: disable=invalid-name


@dataclass
class Machine:
    """Represent information about a pxe-booted machine."""

    mac: Mac
    arch: Arch


class MachineGroup(ABC):
    """Representation of a group of machines."""

    @classmethod
    @abstractmethod
    def matches(cls, machine: Machine) -> bool:
        """Return if the given machine belongs to this group."""
