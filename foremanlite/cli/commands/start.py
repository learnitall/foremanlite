#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Start command group."""
import os

import click

from foremanlite.cli.cli import Config
from foremanlite.logging import setup as setup_logging
from foremanlite.serve.app import setup, start
from foremanlite.vars import LOGFILE_NAME


@click.command()
@click.pass_context
def cli(ctx):
    """Start foremanlite server."""

    config: Config = ctx.obj
    setup_logging(
        verbose=config.verbose,
        use_file=config.persist_log,
        file_path=os.path.join(config.log_dir, LOGFILE_NAME),
        use_stream=(not config.quiet),
    )
    setup(config=config)
    start()
