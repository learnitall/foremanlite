#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Version command group"""
import logging
import typing as t

import click
from prettytable import PrettyTable

from foremanlite.cli.cli import Config, config_to_click
from foremanlite.cli.config import MachineConfig
from foremanlite.logging import get as get_logger
from foremanlite.logging import setup as setup_logging
from foremanlite.machine import SHA256, Arch, Mac, Machine, get_uuid
from foremanlite.serve.context import ServeContext
from foremanlite.store import BaseMachineStore


def _preflight_logger(config: Config):
    """Setup correct logger instance for a command given Config."""

    if config.verbose:
        setup_logging(verbose=True, use_file=False, use_stream=True)
        logger = get_logger("provision")
    else:
        logger = logging.getLogger("_dumb_logger")
        logger.disabled = True

    return logger


def _preflight_store(
    config: Config, logger: logging.Logger
) -> BaseMachineStore:
    """
    Perform preflight checks on commands that expect a store.

    Raises
    ------
    ValueError
        If store is not configured properly.
    """

    store: t.Optional[BaseMachineStore] = ServeContext.get_store(
        config, logger=logger
    )

    if store is None:
        click.echo("No store configured, doing nothing.")
        raise ValueError

    return store


def _preflight_machine(**kwargs) -> t.Tuple[str, str, SHA256]:
    """
    Perform preflight checks on commands that expect a machine.

    Raises
    ------
    ValueError
        If machine was not given properly
    """

    mac = kwargs.get("mac", None)
    arch = kwargs.get("arch", None)
    if mac is None or arch is None:
        click.echo("Need both a mac and arch to continue, doing nothing.")
        raise ValueError

    mac = Mac(mac)
    arch = Arch(arch)
    return mac, arch, get_uuid(mac=mac, arch=arch)


def print_machines(config: Config, **kwargs):
    """Print all know machines given the Config instance."""

    logger = _preflight_logger(config)
    try:
        store = _preflight_store(config, logger)
    except ValueError:
        return

    if any(kwarg is not None for kwarg in kwargs.values()):
        machines = store.find(**kwargs)
    else:
        machines = store.all()

    groups_dir = ServeContext.get_dirs(config, logger=logger)[2]
    group_set = ServeContext.get_group_set(groups_dir, logger=logger)

    table = PrettyTable()
    table.field_names = [
        "name",
        "mac",
        "arch",
        "provision",
        "groups",
        "vars",
    ]
    for machine in machines:
        machine_groups = sorted(
            group_set.filter(machine), key=lambda group: group.name
        )
        group_names = "\n".join([group.name for group in machine_groups])
        group_vars = {}
        for group in machine_groups:  # note the sorting above
            logger.warning(group)
            if group.vars is not None:
                group_vars.update(group.vars)
        group_vars_str = "\n".join(
            [f"{key}={value}" for key, value in group_vars.items()]
        )
        table.add_row(
            [
                repr(machine.name),
                repr(machine.mac),
                repr(machine.arch.value),
                repr(machine.provision),
                group_names,
                group_vars_str,
            ]
        )

    click.echo(table)


def add_machine(config: Config, **kwargs):
    """Add the given machine to the store."""

    logger = _preflight_logger(config)
    try:
        store = _preflight_store(config, logger)
        mac, arch, uuid = _preflight_machine(**kwargs)
    except ValueError:
        return

    if store.get(uuid) is None:
        store.put(Machine(**kwargs))
    else:
        click.echo(
            f"Machine with mac {mac} and arch {arch} already exists "
            f"(uuid {uuid}). Exiting."
        )


def delete_machine(config: Config, **kwargs):
    """Delete the given machine from the store."""

    logger = _preflight_logger(config)
    try:
        store = _preflight_store(config, logger)
        mac, arch, uuid = _preflight_machine(**kwargs)
    except ValueError:
        return

    if store.get(uuid) is not None:
        store.delete(uuid)
    else:
        click.echo(
            f"Could not find given machine described by mac {mac} "
            f"and arch {arch}."
        )


def update_machine(config: Config, **kwargs):
    """Update the given machine in the store."""

    logger = _preflight_logger(config)
    try:
        store = _preflight_store(config, logger)
        mac, arch, uuid = _preflight_machine(**kwargs)
    except ValueError:
        return

    machine = store.get(uuid)
    if machine is None:
        click.echo(
            f"Could not find given machine described by mac {mac} "
            f"and arch {arch}."
        )
        return

    click.echo(
        "Found machine described by the given attributes: " f"{machine.json()}"
    )
    for key, value in kwargs.items():
        setattr(machine, key, value)

    click.echo(f"Updated machine: {machine.json()}")
    store.put(machine)


@click.group()
@click.pass_context
def cli(_, **__):
    """
    Subcommands for working with machines.

    If verbose is given, debug logs will be printed to the screen.
    """


@cli.command()
@click.pass_context
def ls(ctx, **kwargs):  # pylint: disable=invalid-name
    """
    Print information regarding known machines.

    If no arguments are given, then all machines are printed.
    The arguments which are given are used to filter the resulting
    machines printed to the screen.

    If available, information regarding the groups each machine
    belongs to will also be printed.
    """

    config: Config = ctx.obj
    print_machines(config, **kwargs)


@cli.command()
@config_to_click(MachineConfig)
@click.pass_context
def add(ctx, **kwargs):
    """
    Add the given machine to the store.

    Must configure a store and pass at least both a mac and an arch.
    If no store is configured or if both the mac and arch aren't given,
    no action is performed.

    If a machine already exists with the given mac/arch combo, then
    no action is performed.
    """

    config: Config = ctx.obj
    add_machine(config, **kwargs)


@cli.command()
@config_to_click(MachineConfig)
@click.pass_context
def delete(ctx, **kwargs):
    """
    Delete the given machine from the store.

    Must configure a store and pass at least both a mac and an arch.
    If no store is configured or if both the mac and arch aren't given,
    no action is performed.

    If a machine does not exist with the given mac/arch combo, then
    no action is performed.
    """

    config: Config = ctx.obj
    delete_machine(config, **kwargs)


@cli.command()
@config_to_click(MachineConfig)
@click.pass_context
def update(ctx, **kwargs):
    """
    Update the given machine in the store.

    Must configure a store and pass at least both a mac and an arch.
    If no store is configured or if both the mac and arch aren't given,
    no action is performed.

    If a machine does not exist with the given mac/arch combo, then
    no action is performed.
    """

    config: Config = ctx.obj
    update_machine(config, **kwargs)
