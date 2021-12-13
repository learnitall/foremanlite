#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Start command group."""
import click
from foremanlite.cli.cli import cli

@click.command()
def cli():
    click.echo('test')