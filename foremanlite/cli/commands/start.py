#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Start command group."""
import click

from foremanlite.logging import setup as setup_logging


@click.command()
@click.pass_context
def cli(ctx):
    """Start foremanlite server."""
