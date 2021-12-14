#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Start command group."""
import click


@click.command()
def cli():
    """Definition of the start command."""
    click.echo("test")
