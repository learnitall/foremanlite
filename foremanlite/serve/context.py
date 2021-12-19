#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Set variables needed for the app at runtime."""
import logging
import os
import typing as t
from dataclasses import dataclass

import redis

from foremanlite.cache import FileSystemCache
from foremanlite.cli.config import Config
from foremanlite.logging import get as get_logger
from foremanlite.machine import MachineGroup
from foremanlite.store import BaseMachineStore, RedisMachineStore
from foremanlite.vars import DATA_DIR, GROUPS_DIR


@dataclass
class ServeContext:
    """
    Set variables needed at runtime for running web-stuffs.

    Assumes logging has already been setup.
    """

    config: Config
    fs_cache: FileSystemCache
    store: t.Optional[BaseMachineStore]
    groups: t.List[MachineGroup]

    @staticmethod
    def get_store(
        config: Config, logger: logging.Logger
    ) -> t.Optional[BaseMachineStore]:
        """Get instance of BaseMachineStore from the given Config."""

        store = None
        if config.redis:
            logger.info("Using redis machine store")
            store = RedisMachineStore(redis.from_url(config.redis_url))
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

        def on_error(err: OSError):
            logger.warning(
                f"Error occurred while looking for group files: {err}"
            )

        logger.info(f"Looking for group files in {groups_dir}")
        while len(queue_dir) > 0:
            for (path, dirs, files) in os.walk(
                queue_dir.pop(), onerror=on_error
            ):
                queue_dir.extend(dirs)
                files = [file for file in files if is_json(file)]
                group_files.extend(
                    [os.path.join(path, file) for file in files]
                )

        for group_file in group_files:
            try:
                with open(
                    group_file, "r", encoding="utf-8"
                ) as group_file_handler:
                    groups.append(
                        MachineGroup.from_json(group_file_handler.read())
                    )
            except (OSError, ValueError) as err:
                logger.error(f"Unable to parse group file {group_file}: {err}")
                raise err

        group_names = [group.name for group in groups]
        if len(group_names) > 0:
            logger.info(f"Read the following groups: {', '.join(group_names)}")
        else:
            logger.info("No groups were found.")
        return groups

    @staticmethod
    def get_cache(config: Config, logger: logging.Logger) -> FileSystemCache:
        """Get FileSystemCache instance from the given config."""

        data_dir = os.path.abspath(os.path.join(config.config_dir, DATA_DIR))
        try:
            cache = FileSystemCache(data_dir)
        except ValueError as err:
            logger.error(
                "Unable to create handler for data directory "
                f"{data_dir}: {err}"
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
        )

    def start(self):
        """Run one-time startup tasks."""

        if isinstance(self.store, RedisMachineStore):
            self.store.ping()

        self.fs_cache.start_watchdog()

    def stop(self):
        """Run one-time teardown tasks."""

        self.fs_cache.stop_watchdog()


_CONTEXT: ServeContext


def get_context() -> ServeContext:
    """Return the current ServeContext instance."""

    return _CONTEXT


def set_context(ctx: ServeContext):
    """Set the current context to the given ServeContext."""

    global _CONTEXT
    _CONTEXT = ctx
