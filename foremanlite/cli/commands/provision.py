#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Version command group"""
import logging
import typing as t

import click

from foremanlite.cli.cli import Config, config_to_click
from foremanlite.cli.config import MachineConfig
from foremanlite.logging import get as get_logger
from foremanlite.logging import setup as setup_logging
from foremanlite.serve.context import ServeContext
from foremanlite.store import BaseMachineStore


def toggle_provision(config: Config, **kwargs):
    """Toggle the given machine's provision state."""

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

    result = store.find(**kwargs)
    logger.info(result)
    if len(result) == 0:
        click.echo(
            "Could not find given machine described by given attributes: "
            f"{kwargs}"
        )
        return
    if len(result) == 1:
        machine = result.pop()
        click.echo(
            "Found machine described by the given attributes: "
            f"{machine.to_json()}"
        )
        if machine.provision is None:
            click.echo("Provision attribute is None, setting to True")
            machine.provision = True
        else:
            machine.provision = not machine.provision
            click.echo(f"Setting provision attribute to {machine.provision}")
        store.put(machine)
        return
    if len(result) > 1:
        click.echo(
            "More than one machine is described by the given attributes "
            f"(found {len(result)}): {kwargs} -> {result}"
        )


@click.command()
@config_to_click(MachineConfig)
@click.pass_context
def cli(ctx, **kwargs):
    """
    Toggle provisioning for the given machine.

    If verbose is given, debug logs will be printed to the screen.
    """

    config: Config = ctx.obj
    toggle_provision(config, **kwargs)
