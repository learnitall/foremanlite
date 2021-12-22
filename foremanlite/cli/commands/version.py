#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Version command group"""
import platform

import click

from foremanlite.cli.cli import Config
from foremanlite.vars import VERSION


@click.command()
@click.pass_context
def cli(ctx):
    """
    Print version and exit.

    Use --verbose to get extra platform info.
    """

    config: Config = ctx.obj
    if config.verbose:
        click.echo(
            f"Foremanlite {VERSION} on "
            f"{' '.join(platform.architecture()).strip()} "
            f"with Python {platform.python_version()}"
        )
    else:
        click.echo(VERSION)
