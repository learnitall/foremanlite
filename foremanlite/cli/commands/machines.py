#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Version command group"""
import logging
import typing as t

import click
from beautifultable import BeautifulTable

from foremanlite.cli.cli import Config, config_to_click
from foremanlite.cli.config import MachineConfig
from foremanlite.logging import get as get_logger
from foremanlite.logging import setup as setup_logging
from foremanlite.serve.context import ServeContext
from foremanlite.store import BaseMachineStore


def print_machines(config: Config, **kwargs):
    """Print all know machines given the Config instance."""

    if config.verbose:
        setup_logging(verbose=True, use_file=False, use_stream=True)
        logger = get_logger("provision")
    else:
        logger = logging.getLogger("_dumb_logger")
        logger.disabled = True

    store: t.Optional[BaseMachineStore] = ServeContext.get_store(
        config, logger=logger
    )

    if store is None:
        click.echo("No store configured, doing nothing.")
        return

    if any(kwarg is not None for kwarg in kwargs.values()):
        machines = store.find(**kwargs)
    else:
        machines = store.all()

    groups_dir = ServeContext.get_dirs(config, logger=logger)[2]
    group_set = ServeContext.get_group_set(groups_dir, logger=logger)

    table = BeautifulTable()
    table.columns.header = [
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
        group_names = ", ".join([group.name for group in machine_groups])
        group_vars = {}
        for group in machine_groups:  # note the sorting above
            if group.vars is not None:
                group_vars.update(group.vars)
        group_vars_str = ", ".join(
            [f"{key}={value}" for key, value in group_vars.items()]
        )
        table.rows.append(
            [
                machine.name,
                machine.mac,
                machine.arch,
                machine.provision,
                group_names,
                group_vars_str,
            ]
        )

    click.echo(table)


@click.command()
@config_to_click(MachineConfig)
@click.pass_context
def cli(ctx, **kwargs):
    """
    Print information regarding known machines.

    If no arguments are given, then all machines are printed.
    The arguments which are given are used to filter the resulting
    machines printed to the screen.

    If available, information regarding the groups each machine
    belongs to will also be printed.

    If verbose is given, debug logs will be printed to the screen.
    """

    config: Config = ctx.obj
    print_machines(config, **kwargs)
