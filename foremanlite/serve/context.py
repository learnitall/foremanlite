#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Set variables needed for the app at runtime."""
import logging
import os
import typing as t
from dataclasses import dataclass
from pathlib import Path

import redis

from foremanlite.cli.config import Config
from foremanlite.fsdata import FileSystemCache
from foremanlite.logging import get as get_logger
from foremanlite.machine import (
    DirectoryMachineGroupSetWatchdog,
    MachineGroupSet,
    load_groups_from_dir,
)
from foremanlite.store import BaseMachineStore, RedisMachineStore
from foremanlite.vars import (
    CACHE_POLLING_INTERVAL,
    DATA_DIR,
    EXEC_DIR,
    GROUPS_DIR,
)

_dumb_logger = logging.getLogger("_dumb_logger")
_dumb_logger.disabled = True


@dataclass
class ServeContext:
    """
    Set variables needed at runtime for running web-stuffs.

    Assumes logging has already been setup.
    """

    config: Config
    config_dir: Path
    groups_dir: Path
    data_dir: Path
    exec_dir: Path
    log_dir: Path
    cache: FileSystemCache
    store: t.Optional[BaseMachineStore]
    groups: MachineGroupSet
    groups_watchdog: DirectoryMachineGroupSetWatchdog

    @staticmethod
    def get_dirs(
        config: Config, logger: logging.Logger = _dumb_logger
    ) -> t.Tuple[Path, Path, Path, Path, Path]:
        """Return config, data and groups directories."""

        config_dir = Path(config.config_dir).absolute()
        data_dir = config_dir / DATA_DIR
        groups_dir = config_dir / GROUPS_DIR
        exec_dir = config_dir / EXEC_DIR
        log_dir = Path(config.log_dir).absolute()

        dirs = (
            ("config", config_dir),
            ("data", data_dir),
            ("groups", groups_dir),
            ("exec", exec_dir),
            ("log", log_dir),
        )
        for name, directory in dirs:
            if not os.path.exists(directory):
                # Exception lies in the log directory
                # If no-persist was given, don't need to check
                # for it
                if not (name == "log" and not config.persist_log):
                    raise ValueError(
                        f"{name.upper()} directory does not exist, unable to "
                        f"start: {directory}"
                    )

        logger.info(
            f"Using the following directories: config: {str(config_dir)}, "
            f"data: {str(data_dir.relative_to(config_dir))}, "
            f"groups: {str(groups_dir.relative_to(config_dir))}, "
            f"exec: {str(exec_dir.relative_to(config_dir))}, "
            f"log: {str(log_dir)}"
        )

        return config_dir, data_dir, groups_dir, exec_dir, log_dir

    @staticmethod
    def get_store(
        config: Config, logger: logging.Logger = _dumb_logger
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
    def get_group_set(
        groups_dir: Path, logger: logging.Logger = _dumb_logger
    ) -> MachineGroupSet:
        """Get MachineGroupSet using the given config"""

        groups = load_groups_from_dir(
            groups_dir=groups_dir,
            cache=None,
            logger=logger,
        )
        return MachineGroupSet(groups=groups)

    @staticmethod
    def get_group_watchdog(
        groups_dir: Path,
        groups: MachineGroupSet,
        cache: FileSystemCache,
    ) -> DirectoryMachineGroupSetWatchdog:
        """Get DirectoryMachineGroupSetWatchdog using the given config"""

        return DirectoryMachineGroupSetWatchdog(
            groups_dir=groups_dir,
            cache=cache,
            polling_interval=CACHE_POLLING_INTERVAL,
            machine_group_set=groups,
        )

    @staticmethod
    def get_cache(
        config: Config, logger: logging.Logger = _dumb_logger
    ) -> FileSystemCache:
        """Get FileSystemCache instance from the given config."""

        data_dir = os.path.abspath(os.path.join(config.config_dir, DATA_DIR))
        try:
            cache = FileSystemCache(
                data_dir,
                max_file_size_bytes=config.max_cache_file_size,
                polling_interval=CACHE_POLLING_INTERVAL,
            )
        except ValueError as err:
            logger.error(
                "Unable to create handler for data directory " "%s: %s",
                data_dir,
                err,
            )
            raise err

        return cache

    @classmethod
    def from_config(cls, config: Config):
        """Create ServeContext using the given Config instance."""

        logger = get_logger("ServeContext")
        config_dir, data_dir, groups_dir, exec_dir, log_dir = cls.get_dirs(
            config, logger
        )
        store = cls.get_store(config, logger)
        cache = cls.get_cache(config, logger)
        group_set = cls.get_group_set(groups_dir, logger)
        group_watchdog = cls.get_group_watchdog(groups_dir, group_set, cache)
        return cls(
            config=config,
            config_dir=config_dir,
            data_dir=data_dir,
            groups_dir=groups_dir,
            exec_dir=exec_dir,
            log_dir=log_dir,
            cache=cache,
            store=store,
            groups=group_set,
            groups_watchdog=group_watchdog,
        )

    def start(self):
        """Run one-time startup tasks."""

        if isinstance(self.store, RedisMachineStore):
            self.store.ping()

        self.cache.start_watchdog()
        self.groups_watchdog.start()

    def stop(self):
        """Run one-time teardown tasks."""

        self.cache.stop_watchdog()
        self.groups_watchdog.stop()


_CONTEXT: ServeContext


def get_context() -> ServeContext:
    """Return the current ServeContext instance."""

    return _CONTEXT


def set_context(ctx: ServeContext):
    """Set the current context to the given ServeContext."""

    global _CONTEXT
    _CONTEXT = ctx
