# -*- coding: utf-8 -*-
"""Representation of machine information."""
import functools
import hashlib
import logging
import os
import re
import threading
import typing as t
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path

import orjson
from pydantic import BaseModel
from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from foremanlite.fsdata import SHA256, DataFile, FileSystemCache
from foremanlite.logging import get as get_logger

Mac = t.NewType("Mac", str)


class Arch(Enum):
    """Represent architecture of a machine."""

    x86_64 = "x86_64"  # pylint: disable=invalid-name
    aarch64 = "aarch64"  # pylint: disable=invalid-name


def _orjson_dumps(value, *_, default):
    """Wrap orjson.dumps to decode to str."""

    return orjson.dumps(value, default=default).decode()


class _MachineStuffsBaseModelConfig:
    """Default Config for MachineStuffs BaseModels"""

    json_loads = orjson.loads
    json_dumps = _orjson_dumps


class _MachineStuffsBaseModel(BaseModel):
    """Pydantic BaseModel for all MachineStuffs that need serialization"""

    class Config(_MachineStuffsBaseModelConfig):
        """Define pydantic configuration by subclassing base model config."""

        ...


class Machine(_MachineStuffsBaseModel):
    """
    Represent information about a pxe-booted machine.

    This definition is coupled with
    foremanlite.serve.util.machine_parser.

    Attributes
    ----------
    name : str, optional
        Pretty-name of the machine.
    mac : Mac
        Mac address of the machine.
    arch : Arch
        Architecture of the machine. Must be part of Arch enum.
    provision: bool, optional
        If True, signals this machine should be provisioned on next boot.
        If False, signals this machine should not be provisioned on next boot.
    """

    mac: Mac
    arch: Arch
    name: t.Optional[str] = None
    provision: t.Optional[bool] = None

    def __eq__(self, other) -> bool:
        return repr(self) == repr(other)

    def __hash__(self):
        return hash(repr(self))


def get_uuid(
    mac: t.Optional[Mac] = None,
    arch: t.Optional[Arch] = None,
    machine: t.Optional[Machine] = None,
) -> SHA256:
    """
    Comput uuid of a machine given a mac and its arch.

    If machine is given, mac and arch will be pulled from the machine.

    Raises
    ------
    ValueError
        if mac and arch are not available.
    """

    if machine is not None:
        mac = machine.mac
        arch = machine.arch

    if mac is None or arch is None:
        raise ValueError(
            "Need mac and arch to compute uuid, one or both "
            f"is missing (mac={mac}, arch={arch}"
        )

    return SHA256(
        hashlib.sha256(f"{str(mac)}{str(arch)}".encode("utf-8")).hexdigest()
    )


class MachineSelectorType(Enum):
    """Define different 'modes' for the MachineSelector class."""

    regex = "regex"  # pylint: disable=invalid-name
    exact = "exact"  # pylint: disable=invalid-name


class MachineSelector(ABC, _MachineStuffsBaseModel):
    """
    Machine Selector matches machines based on attribute values.

    Parameters
    ----------
    type : str
        One of the MachineSelectorTypes.
    attr : str
        Attribute of Machine to match val against.
    val : str
        Value to match against.
    """

    type: MachineSelectorType
    attr: str
    val: str

    def _exact_matches(self, machine: Machine) -> bool:
        """Determine if the machine has the exact expected value."""

        attr = getattr(machine, self.attr, None)
        if attr is None:
            return False
        if isinstance(attr, Enum):
            attr = attr.value

        return attr == self.val

    def _regex_matches(self, machine: Machine) -> bool:
        """Determine if machine has attr which matches set regex string."""

        attr = getattr(machine, self.attr, None)
        if attr is None:
            return False
        if isinstance(attr, Enum):
            attr = attr.value

        return re.match(self.val, attr) is not None

    def matches(self, machine: Machine) -> bool:
        """
        Return if the given machine matches the selector.

        Raises
        ------
        ValueError
            if an invalid MachineSelectorType was given.
        """

        match_method = getattr(self, f"_{str(self.type.value)}_matches", None)
        if match_method is None:
            raise ValueError(
                f"Invalid match type given {self.type} "
                "(expected one of "
                f"{', '.join([m.value for m in MachineSelectorType])})"
            )
        return match_method(machine)


class MachineGroup(_MachineStuffsBaseModel):
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
    vars : dict
        Variables to associate with this group.
    """

    name: str
    selectors: t.List[MachineSelector]
    vars: t.Optional[t.Dict[str, t.Any]] = None
    machines: t.List[Machine] = []

    def __hash__(self):
        return hash(repr(self))

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
                self.machines.append(machine)
                count += 1

        return count


@functools.cache
def _filter_groups(
    machine: Machine, groups: t.Iterable[MachineGroup]
) -> t.Set[MachineGroup]:
    """
    Return the set of all groups the given machine belongs to.

    Parameters
    ----------
    machine : Machine
        Machine to find group membership of.
    groups : iterable of MachineGroup
        Iterable of MachineGroups to sort through.

    Returns
    -------
    set of MachineGroup
        Set of all the MachineGroups that the given Machine belongs to.
    """

    result = set()
    for group in groups:
        if group.matches(machine):
            result.add(group)

    return result


def load_groups_from_dir(
    groups_dir: Path,
    cache: t.Optional[FileSystemCache] = None,
    logger: t.Optional[logging.Logger] = None,
) -> t.List[MachineGroup]:
    """
    Load a set of groups from files in the given directory (recursive).

    Will recursively look in the given `groups_dir` for json files. Any
    json file found will be treated as a group definition.

    Parameters
    ----------
    groups_dir : Path
        Directory containing json files defining MachineGroup instances.
        See `MachineGroup.from_json` for more information.
    cache : FileSystemCache, optional
        FileSystemCache instance to read files with.
    logger : logging.Logger, optional
        logger to log warnings and issues to.

    Raises
    ------
    ValueError
        if unable to parse group file
    OSError
        if unable to read group file
    """

    if logger is None:
        logger = logging.getLogger("_dumb_logger")
        logger.disabled = True
    groups = []
    group_files: t.List[Path] = []
    # https://www.sethserver.com/python/recursively-list-files.html
    queue_dir: t.List[t.Union[Path, str]] = [groups_dir]
    is_json = lambda f: str(f).endswith(".json")

    def on_error(err: OSError):
        logger.warning("Error occurred while looking for group files: %s", err)

    logger.info("Looking for group files in %s", groups_dir)
    while len(queue_dir) > 0:
        for (path, dirs, files) in os.walk(queue_dir.pop(), onerror=on_error):
            queue_dir.extend(dirs)
            files = [file for file in files if is_json(file)]
            group_files.extend(
                [Path(os.path.join(path, file)) for file in files]
            )

    for group_file in group_files:
        try:
            content = (
                DataFile(Path(group_file), cache=cache).read().decode("utf-8")
            )

            groups.append(MachineGroup.parse_raw(content))
        except (OSError, ValueError) as err:
            logger.error("Unable to parse group file %s: %s", group_file, err)
            raise err

    return groups


class _MachineGroupSetLockRegistry:
    """
    Registry for locks on a MachineGroupSet.

    Each unique MachineGroupSet instance gets its own
    `threading.Lock` instance in the registry. Instances
    are identified using the `id` function.

    Using a registry like this will keep the MachineGroupSet
    pickleable, as it doesn't have to store its own locks as
    an instance attribute.
    """

    registry: t.Dict[int, threading.Lock] = {}

    @classmethod
    def lock(cls, machine_group_set: "MachineGroupSet"):
        """Return threading.Lock instance for given MachineGroupSet."""
        set_id = id(machine_group_set)
        result = cls.registry.get(set_id, None)
        if result is None:
            new_lock = threading.Lock()
            cls.registry[set_id] = new_lock
            result = new_lock
        return result


class MachineGroupSet(_MachineStuffsBaseModel):
    """
    Manage a set of MachineGroups.

    Accessing groups directly through the `groups` attribute should
    only be done after acquiring the lock at the `lock` attribute.
    All method of this class perform said acquire/release
    automatically. This keeps the set of groups thread-safe, for
    use cases such as the `MachineGroupSetWatchdog`.

    Parameters
    ----------
    groups : set of MachineGroup
        Set of MachineGroup instances to manage.
    """

    groups: t.List[MachineGroup]

    def all(self) -> t.List[MachineGroup]:
        """Return the set of all groups in the MachineGroupSet"""

        with _MachineGroupSetLockRegistry.lock(self):
            return self.groups

    def filter(self, machine: Machine) -> t.Set[MachineGroup]:
        """
        Return the set of all groups the given machine belongs to.

        Parameters
        ----------
        machine : Machine
            Machine to find group membership of.
        groups : iterable of MachineGroup
            Iterable of MachineGroups to sort through.

        Returns
        -------
        set of MachineGroup
            Set of all the MachineGroups that the given Machine belongs to.
        """

        # need to cast to tuple since that is hashable and _filter_groups
        # is wrapped with functools.cache
        with _MachineGroupSetLockRegistry.lock(self):
            return _filter_groups(machine, tuple(self.groups))


class MachineGroupSetWatchdog(ABC):
    """
    Continually update a MachineGroupSet.

    Parameters
    ----------
    machine_group_set : MachineGroupSet
        MachineGroupSet to update over time.
    """

    def __init__(self, machine_group_set: MachineGroupSet):
        self.machine_group_set = machine_group_set

    @abstractmethod
    def start(self):
        """Start the watchdog."""

    @abstractmethod
    def stop(self):
        """Stop the watchdog."""


class _DMGSWEventHandler(FileSystemEventHandler):
    """Event handler for DirectoryMachineGroupSetWatchdog."""

    def __init__(self, watchdog: "DirectoryMachineGroupSetWatchdog"):
        super().__init__()
        self.watchdog = watchdog

    def on_modified(self, _: FileModifiedEvent):
        """Callback for modified event."""

        self.watchdog.reload()


class DirectoryMachineGroupSetWatchdog(MachineGroupSetWatchdog):
    """
    Watch a directory of machine group json files.

    Has the same args and kwargs as super class `MachineGroupSetWatchdog`
    with the following additions:

    Parameters
    ----------
    groups_dir : Path
        Directory of MachineGroup json files to watch for changes.
    cache : FileSystemCache
        FileSystemCache instance to use for reading group files
        off of the file system.
    polling_interval : float, 1.0
        Interval in-between polling directory for changes.
        Defaults to 1 second.
    """

    def __init__(
        self,
        groups_dir: Path,
        cache: FileSystemCache,
        *args,
        polling_interval: float = 1.0,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.groups_dir = groups_dir
        self.cache = cache
        self.logger = get_logger("DirectoryMachineGroupSetWatchdog")
        self.observer = PollingObserver(timeout=polling_interval)
        self.logger.info(f"Watching group directory '{str(self.groups_dir)}'")

    def reload(self):
        """Reload the groups in the MachineGroupSet."""

        new_groups = load_groups_from_dir(
            self.groups_dir, self.cache, self.logger
        )
        with _MachineGroupSetLockRegistry.lock(self.machine_group_set):
            self.machine_group_set.groups = new_groups

    def start(self):
        self.observer.schedule(
            _DMGSWEventHandler(self), self.groups_dir, recursive=False
        )
        self.observer.start()
        self.logger.info("Started DirectoryMachineGroupSet watchdog")

    def stop(self):
        self.logger.info("Stopping DirectoryMachineGroupSet watchdog")
        self.observer.stop()
        self.observer.join()
