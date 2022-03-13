#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Version command group"""
import json
import logging

import click
import orjson

from foremanlite.cli.config import Config
from foremanlite.logging import get as get_logger
from foremanlite.logging import setup as setup_logging
from foremanlite.serve.context import ServeContext


def print_groups(config: Config):
    """Print all known groups given the Config instance."""

    if config.verbose:
        setup_logging(verbose=True, use_file=False, use_stream=True)
        logger = get_logger("provision")
    else:
        logger = logging.getLogger("_dumb_logger")
        logger.disabled = True

    group_dir = ServeContext.get_dirs(config, logger=logger)[2]
    machine_group_set = ServeContext.get_group_set(
        group_dir, cache=None, logger=logger
    )
    click.echo(json.dumps(orjson.loads(machine_group_set.json()), indent=4))


@click.command()
@click.pass_context
def cli(ctx):
    """
    Print all known groups in json and exit.

    If verbose is given, debug logs will be printed to the screen.
    """

    config: Config = ctx.obj
    print_groups(config)
