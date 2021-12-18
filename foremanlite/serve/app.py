#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configure variables for flask startup."""
import logging
import os
import typing as t
from dataclasses import dataclass

from foremanlite.cache import FileSystemCache
from foremanlite.cli.config import Config
from foremanlite.logging import get as get_logger
from foremanlite.machine import MachineGroup
from foremanlite.store import BaseMachineStore, RedisMachineStore

DATA_DIR = "data"
GROUPS_DIR = "groups"


@dataclass
class ServeContext:
    """Set variables needed at runtime for running web-stuffs."""

    config: Config
    fs_cache: FileSystemCache
    store: t.Optional[BaseMachineStore]
    groups: t.List[MachineGroup]
    _logger: logging.Logger

    @staticmethod
    def get_store(
        config: Config, logger: logging.Logger
    ) -> t.Optional[BaseMachineStore]:
        """Get instance of BaseMachineStore from the given Config."""

        store = None
        if config.redis:
            logger.info("Using redis machine store")
            store = RedisMachineStore(url=config.redis_url)
        else:
            logger.warning("No machine store was configured")
        return store

    @staticmethod
    def get_groups(
        config: Config, logger: logging.Logger
    ) -> t.List[MachineGroup]:
        """
        Get list of MachineGroups using the given Config.

        Will recursively look in the given config's configuration
        directory under `GROUPS_DIR` for any json files. These
        json files will be treated as group definitions.
        """

        groups = []
        group_files = []
        groups_dir = os.path.join(config.config_dir, GROUPS_DIR)
        # https://www.sethserver.com/python/recursively-list-files.html
        queue_dir = [groups_dir]
        is_json = lambda f: os.path.splitext(f) == ".json"

        logger.info(f"Looking for group files in {groups_dir}")
        while len(queue_dir) > 0:
            for (path, dirs, files) in os.walk(queue_dir.pop()):
                queue_dir.extend(dirs)
                files = [file for file in files if is_json(file)]
                group_files.extend(
                    [os.path.join(path, file) for file in files]
                )

        for group_file in group_files:
            try:
                with open(group_file, "r") as group_file_handler:
                    groups.append(
                        MachineGroup.from_json(group_file_handler.read())
                    )
            except (OSError, ValueError) as err:
                logger.error(f"Unable to parse group file {group_file}: {err}")
                raise err

        group_names = [group.name for group in groups]
        logger.info(f"Read the following groups: {', '.join(group_names)}")
        return groups

    @staticmethod
    def get_cache(config: Config, logger: logging.Logger) -> FileSystemCache:
        """Get FileSystemCache instance from the given config."""

        data_dir = os.path.join(config.config_dir, DATA_DIR)
        try:
            cache = FileSystemCache(data_dir)
        except ValueError as err:
            logger.error(
                f"Unable to create handler for data directory {data_dir}: {err}"
            )
            raise err

        return cache

    @classmethod
    def from_config(cls, config: Config):
        """Create ServeContext using the given Config instance."""

        logger = get_logger("ServeContext")
        store = cls.get_store(config, logger)
        fs_cache = cls.get_cache(config, logger)
        groups = cls.get_groups(config, logger)
        return cls(
            config=config,
            fs_cache=fs_cache,
            store=store,
            groups=groups,
            _logger=logger,
        )

    def start(self):
        """Run one-time startup tasks."""

        if isinstance(self.store, RedisMachineStore):
            self.store.ping()
