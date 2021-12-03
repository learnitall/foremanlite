# -*- coding: utf-8 -*-
"""Representation of machine information."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import NewType
from enum import Enum

Mac = NewType('Mac', int)


class Arch(Enum):
    """Represent architecture of a machine."""
    x86_64 = 1
    aarch64 = 2


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

