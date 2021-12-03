# -*- coding: utf-8 -*-
"""Options for storing and retrieving information about a machine."""
from abc import ABC, abstractmethod
from foremanlite.machine import Machine, Mac


class BaseStore(ABC):
    """ABC for a machine storage utility."""

    @abstractmethod
    def put(machine: Machine):
        """Put the given machine into the store."""

    @abstractmethod
    def get(mac: Mac) -> Machine:
        """Get the given machine from the store (by Mac)."""

