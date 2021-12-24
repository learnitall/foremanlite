# -*- coding: utf-8 -*-
"""Options for storing and retrieving information about a machine."""
import json
import typing as t
from abc import ABC, abstractmethod
from dataclasses import asdict

import redis

from foremanlite.logging import get as get_logger
from foremanlite.machine import SHA256, Machine, get_uuid


class BaseMachineStore(ABC):
    """ABC for a machine storage utility."""

    @abstractmethod
    def put(self, machine: Machine):
        """Put the given machine into the store."""

    @abstractmethod
    def get(self, uuid: SHA256) -> t.Optional[Machine]:
        """Get machine from the store with the given uuid."""

    @abstractmethod
    def find(self, **kwargs) -> t.Set[Machine]:
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
        try:
            self.redis.ping()
        except redis.exceptions.ConnectionError:
            self.logger.warning(
                f"Unable to establish connection with redis host at {host}"
            )
            return False
        else:
            self.logger.info(f"Connected to redis at {host}")
            return True

    def put(self, machine: Machine):
        """Store the given machine."""

        uuid = get_uuid(machine=machine)
        self.redis.set(uuid, machine.to_json())
        machines = self.redis.get(self.MACHINES_KEY)
        if machines is None:
            self.redis.set(self.MACHINES_KEY, f'["{uuid}"]')
        else:
            machine_list = json.loads(machines)
            machine_list.append(uuid)
            self.redis.set(self.MACHINES_KEY, json.dumps(machine_list))
        self.logger.info(f"Added machine with uuid {uuid}")
        self.logger.debug(f"Machine with {uuid}: {machine}")

    def get(self, uuid: SHA256) -> t.Optional[Machine]:
        """Return the machine with the given uuid."""

        result: t.Optional[str] = self.redis.get(uuid)
        if result is not None:
            return Machine.from_json(result)
        return None

    def all(self) -> t.Set[Machine]:
        """Return set of all machines in the redis store."""

        result: t.Set[Machine] = set()
        machines = self.redis.get(self.MACHINES_KEY)
        if machines is None:
            return result
        uuid_list = json.loads(machines)
        for machine_uuid in uuid_list:
            machine_json = self.redis.get(machine_uuid)
            if machine_json is None:
                continue
            result.add(Machine.from_json(machine_json))
        return result

    def find(self, **kwargs) -> t.Set[Machine]:
        """Return set of machines based on given kwargs."""

        result: t.Set[Machine] = set()
        machines = self.all()
        if len(machines) == 0:
            return result

        kwargs_set = set(kwargs.items())
        for machine in machines:
            print(machine)
            if kwargs_set.issubset(set(asdict(machine).items())):
                print("match")
                result.add(machine)

        return result
