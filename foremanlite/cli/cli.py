#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create cli interface for foremanlite, ready to be loaded by main.

We use a Multi Command structure and lazily load files from `cli.commands`.

See click documentation at
https://click.palletsprojects.com/en/8.0.x/commands/#custom-multi-commands
for more info.
"""
import os
import typing as t

import click
import click_config_file
from click import Context

from foremanlite.logging import setup as logging_setup

COMMAND_FOLDER = os.path.join(os.path.dirname(__file__), "commands")


class ForemanliteCLI(click.MultiCommand):
    """Define MultiCommand CLI that loads from `COMMAND_FOLDER`."""

    @staticmethod
    def list_commands(_: Context) -> t.List[str]:
        """
        Get list of command files.

        Return
        ------
        list of str
        """

        commands = []
        for filename in os.listdir(COMMAND_FOLDER):
            if filename.endswith(".py") and filename != "__init__.py":
                commands.append(filename.removesuffix(".py"))
        commands.sort()
        return commands

    @staticmethod
    def get_command(_: Context, cmd_name: str) -> t.Optional[click.Command]:
        """
        Get command by the given name.

        Parameters
        ----------
        cmd_name : str
            Command name to load. Will look for a python file with this same
            name in `COMMAND_FOLDER`.

        Return
        ------
        none or click.Command
        """

        namespace: t.Dict[str, click.Command] = {}
        filename = os.path.join(COMMAND_FOLDER, cmd_name + ".py")
        with open(filename, encoding="utf-8") as pyfile:
            code = compile(pyfile.read(), filename, "exec")
            eval(code, namespace, namespace)
        return namespace["cli"]


@click.command(cls=ForemanliteCLI)
@click.option(
    "--verbose/--no-verbose", default=False, help="Enable verbose logging"
)
@click.option(
    "--quiet/--no-quiet", default=False, help="Disable printing logs to screen"
)
@click.option(
    "--log-file",
    default="/var/log/foremanlite/foremanlite.log",
    help="Provide filename to log file",
)
@click.option(
    "--persist-log/--no-persist-log",
    default=False,
    help="Persist logs on disk to given log file. File rotation will be used.",
)
@click.option(
    "--config-dir",
    default="/etc/foremanlite/",
    help="Path to configuration directory.",
)
@click_config_file.configuration_option()
@click.pass_context
def cli(ctx, verbose, quiet, log_file, persist_log, config_dir, plugin_dir):
    """
    Main function for foremanlite cli.

    This function is first called upon using the foremanlite cli.
    """
    ctx.ensure_obj(dict)
    ctx.obj["CONFIG_DIR"] = config_dir
    ctx.obj["PLUGIN_DIR"] = plugin_dir
    logging_setup(
        verbose=verbose,
        use_file=persist_log,
        file_path=log_file,
        use_stream=not quiet,
    )


def run():
    """Start the foremanlite cli"""
    ForemanliteCLI(help="foremanlite CLI")
    cli()  # pylint: disable=no-value-for-parameter


if __name__ == "__main__":
    run()
