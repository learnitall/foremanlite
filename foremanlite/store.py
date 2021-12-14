# -*- coding: utf-8 -*-
"""Options for storing and retrieving information about a machine."""
from abc import ABC, abstractmethod

from foremanlite.machine import Mac, Machine


class BaseMachineStore(ABC):
    """ABC for a machine storage utility."""

    @abstractmethod
    def put(self, machine: Machine):
        """Put the given machine into the store."""

    @abstractmethod
    def get(self, mac: Mac) -> Machine:
        """Get the given machine from the store (by Mac)."""
