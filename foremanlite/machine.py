# -*- coding: utf-8 -*-
"""Representation of machine information."""
import functools
import hashlib
import json
import logging
import os
import re
import threading
import typing as t
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

from watchdog.events import FileModifiedEvent, FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from foremanlite.fsdata import SHA256, DataFile, FileSystemCache
from foremanlite.logging import get as get_logger

Mac = t.NewType("Mac", str)


class Arch(Enum):
    """Represent architecture of a machine."""

    x86_64 = "x86_64"  # pylint: disable=invalid-name
    aarch64 = "aarch64"  # pylint: disable=invalid-name


@dataclass
class Machine:
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

    def to_json(self, **kwargs) -> str:
        """
        Return json-formatting string of Machine instance.

        Any kwargs passed will be given to `json.dumps`.

        Examples
        --------
        >>> from foremanlite.machine import Machine
        >>> m = Machine(name="test", mac="11:22:33:44", arch="x86_64")
        >>> m.to_json()
        '{"mac": "11:22:33:44", "arch": "x86_64", "name": "test", "provision": null}'
        """  # pylint: disable=line-too-long

        result = asdict(self)
        result["arch"] = str(self.arch.value)
        result["mac"] = str(self.mac)
        return json.dumps(result, **kwargs)

    @classmethod
    def from_json(cls, json_str: str) -> "Machine":
        """Return Machine from json-formatted string."""

        result = json.loads(json_str)
        result["arch"] = Arch(result["arch"])
        result["mac"] = Mac(result["mac"])
        return cls(**result)


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


class MachineSelector(ABC):
    """Base Machine Selector class."""

    @abstractmethod
    def matches(self, machine: Machine) -> bool:
        """Return if the given machine matches the selector."""

    @abstractmethod
    def to_json(self, **kwargs) -> str:
        """
        Return json representation of the selector.

        Any kwargs passed will be given to `json.dumps`.
        """


class ExactMachineSelector(MachineSelector):
    """
    ExactMachineSelector matches machines based on expected attribute values.

    Parameters
    ----------
    attr : str
        Attribute of Machine to match val against.
    val : str
        Value to match against.
    """

    def __init__(self, attr: str, val: str):
        self.val: str = val
        self.attr: str = attr

    def matches(self, machine: Machine) -> bool:
        attr = getattr(machine, self.attr, None)
        if attr is None:
            return False
        if isinstance(attr, Enum):
            attr = attr.value

        return attr == self.val

    def to_json(self, **kwargs) -> str:
        return json.dumps(
            {"type": "exact", "val": self.val, "attr": self.attr}, **kwargs
        )


class RegexMachineSelector(MachineSelector):
    """
    RegexMachineSelector matches Machines based on regex strings.

    Match must be exact (i.e. from beginning of string).
    Regex search will not be performed.

    Parameters
    ----------
    attr : str
        Attribute of Machine to match regex string against.
    val : str
        Regex string to match against.
    """

    def __init__(self, attr: str, val: str):
        self.reg: str = val
        self.attr: str = attr

    def matches(self, machine: Machine) -> bool:
        """
        Determine if this selector matches the given matchine.

        Parameters
        ----------
        machine : Machine
            Machine to determine if selection matches

        Returns
        -------
        bool
        """

        attr = getattr(machine, self.attr, None)
        if attr is None:
            return False
        if isinstance(attr, Enum):
            attr = attr.value

        return re.match(self.reg, attr) is not None

    def to_json(self, **kwargs) -> str:
        return json.dumps(
            {"type": "regex", "val": self.reg, "attr": self.attr}, **kwargs
        )


class MachineGroup:
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
    group_vars : dict
        Variables to associate with this group.
    """

    SELECTORS = {
        "exact": ExactMachineSelector,
        "regex": RegexMachineSelector,
    }

    def __init__(
        self,
        name: str,
        selectors: t.Iterable[MachineSelector],
        group_vars: t.Optional[t.Dict[str, t.Any]] = None,
    ):
        self.name = name
        self.selectors = selectors
        self.machines: t.Set[Machine] = set()
        self.vars = group_vars

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
                self.machines.add(machine)
                count += 1

        return count

    def to_json(self, **kwargs) -> str:
        """Return json representation of the MachineGroup."""

        selectors = []
        for selector in self.selectors:
            selectors.append(json.loads(selector.to_json()))
        return json.dumps(
            {
                "name": self.name,
                "vars": self.vars,
                "selectors": selectors,
            },
            **kwargs,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "MachineGroup":
        """
        Parse a MachineGroup from the given json string.

        Expected format:

        ```
        {
            "name": name,
            "selectors": [
                {
                    "type": type,
                    "attr": attr,
                    "val": val
                },
                ...
            ],
            "vars": {
                var1: value1,
                ...
            }
        }
        ```

        Parameters
        ----------
        json : str
            json to parse into a MachineGroup instance.

        Raises
        ------
        ValueError
            if the config could not be parsed correctly
        """

        config = json.loads(json_str)
        name, selectors = config.get("name", None), config.get(
            "selectors", None
        )

        if name is None or selectors is None:
            raise ValueError(
                "Expected name and selectors keys, one of them is missing."
            )

        selector_instances = []
        for selector in selectors:
            sel_type = selector.get("type", None)
            if sel_type is None:
                raise ValueError(
                    "Expected type attribute in selector but it is missing: "
                    f"{selector}"
                )

            sel_cls = cls.SELECTORS.get(sel_type.lower(), None)
            if sel_cls is None:
                raise ValueError(
                    f"Could not find selector with name {sel_type}"
                )

            del selector["type"]
            try:
                selector_instances.append(sel_cls(**selector))
            except Exception as err:
                raise ValueError(
                    f"Unable to create selector {sel_type}: {err}"
                )

        return cls(
            name=name,
            selectors=selector_instances,
            group_vars=config.get("vars", None),
        )


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
) -> t.Set[MachineGroup]:
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

            groups.append(MachineGroup.from_json(content))
        except (OSError, ValueError) as err:
            logger.error("Unable to parse group file %s: %s", group_file, err)
            raise err

    return set(groups)


class MachineGroupSet:
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

    def __init__(self, groups: t.Set[MachineGroup]):
        self.groups = groups
        self.lock = threading.Lock()

    def to_json(self, **kwargs) -> str:
        """
        Return json representation of the MachineGroupSet

        Any kwargs given will be passed to `json.dumps`.
        """

        return json.dumps(
            [json.loads(group.to_json()) for group in self.groups], **kwargs
        )

    def all(self) -> t.Set[MachineGroup]:
        """Return the set of all groups in the MachineGroupSet"""

        with self.lock:
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
        with self.lock:
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
        with self.machine_group_set.lock:
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
