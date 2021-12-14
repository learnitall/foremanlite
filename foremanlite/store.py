# -*- coding: utf-8 -*-
"""Options for storing and retrieving information about a machine."""
import json
import typing as t
from abc import ABC, abstractmethod
from dataclasses import asdict

import redis

from foremanlite.logging import get as get_logger
from foremanlite.machine import Machine


class BaseMachineStore(ABC):
    """ABC for a machine storage utility."""

    @abstractmethod
    def put(self, machine: Machine):
        """Put the given machine into the store."""

    @abstractmethod
    def get(self, **kwargs) -> t.Set[Machine]:
        """
        Get machine(s) from the store from the given attributes.

        Any machine which matches on all of these attributes will be returned.
        """

    @abstractmethod
    def all(self) -> t.Set[Machine]:
        """Return set of all machines in the store."""


class RedisMachineStore(BaseMachineStore):
    """
    Store machines into Redis

    A redis connection can be provided if available, otherwise
    any kwargs passed to this instance are given directly to ``redis.Redis``.
    See [redis documentation](https://docs.redis.com/latest/rs/references/
    client_references/client_python/) for more info.
    """

    MACHINES_KEY = "machines"

    def __init__(self, redis_conn: t.Optional[redis.Redis] = None, **kwargs):
        if redis_conn is not None:
            self.redis = redis_conn
        else:
            self.redis = redis.Redis(**kwargs)
        self.logger = get_logger("RedisMachineStore")

    def ping(self) -> bool:
        """Try connecting to configured redis instance, logging results."""

        host = self.redis.connection_pool.connection_kwargs["host"]
        if self.redis.ping():
            self.logger.info(f"Connected to redis at {host}")
            return True

        self.logger.warning(
            f"Unable to establish connection with redis host at {host}"
        )
        return False

    def _get_machine_list(self) -> t.List[Machine]:
        """Get machine list from redis."""

        current_list_str = self.redis.get(self.MACHINES_KEY)
        if current_list_str is None:
            current_list_str = "[]"
        current_list: t.List[str] = json.loads(current_list_str)
        current_machine_list = []
        for machine_json in current_list:
            current_machine_list.append(Machine.from_json(machine_json))
        return current_machine_list

    def _put_machine_list(self, machine_list: t.List[Machine]):
        machine_list_json: t.List[str] = [m.to_json() for m in machine_list]
        self.redis.set(self.MACHINES_KEY, json.dumps(machine_list_json))

    @staticmethod
    def _is_match(machine: Machine, **kwargs):
        """Check that given machine contains all kwargs as fields."""

        kwargs_set = set(kwargs.items())
        machine_set = set(asdict(machine).items())
        return kwargs_set.issubset(machine_set)

    def put(self, machine: Machine):
        """Store the given machine."""

        current_list = self._get_machine_list()
        current_list.append(machine)
        self._put_machine_list(current_list)

    def get(self, **kwargs) -> t.Set[Machine]:
        """Return set of machines based on given kwargs."""

        result = set()
        current_list = self._get_machine_list()
        for machine in current_list:
            if self._is_match(machine, **kwargs):
                result.add(machine)

        return result

    def all(self) -> t.Set[Machine]:
        """Return set of all machines in the redis store."""

        return set(self._get_machine_list())
