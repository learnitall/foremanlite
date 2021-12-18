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
from dataclasses import fields
from functools import cache, reduce

import click
import click_config_file
from click import Context

from foremanlite.cli.config import DEFAULT_CONFIG, Config

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


@cache
def config_to_click(config: Config):
    """Translate config dataclass to click decorators."""
    decs: t.List[t.Callable] = []

    for field in fields(config):
        if field.name.endswith("_help"):
            continue

        name_norm = field.name.lower().replace("_", "-")
        name_param = f"--{name_norm}"
        if field.type == bool:
            name_param += f"/--no-{name_norm}"

        help_str = getattr(config, field.name + "_help", "")
        decs.append(
            click.option(name_param, default=field.default, help=help_str)
        )

    def wrapper(func):
        # Decorators is organized from top of call stack to bottom,
        # so traverse from bottom to top while constructing wrapped function
        # this is why we have decs[::-1]
        return reduce(lambda x, y: y(x), decs[::-1], func)

    return wrapper


@click.command(cls=ForemanliteCLI)
@config_to_click(DEFAULT_CONFIG)
@click_config_file.configuration_option()
@click.pass_context
def cli(ctx, **kwargs):
    """Foremanlite CLI."""
    config = Config(**kwargs)
    ctx.obj = config


def run():
    """Start the foremanlite cli"""
    ForemanliteCLI(help="foremanlite CLI")
    cli()  # pylint: disable=no-value-for-parameter


if __name__ == "__main__":
    run()
