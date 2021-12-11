#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create cli interface for foremanlite, ready to be loaded by main.

We use a Multi Command structure and lazily load files from `cli.commands`.

See [click documentation](https://click.palletsprojects.com/en/8.0.x/commands/#custom-multi-commands)
for more info.
"""
import typing as t
import os
import click
from click import Context
import click_config_file
from foremanlite.logging import setup as logging_setup

COMMAND_FOLDER = os.path.join(os.path.dirname(__file__), 'commands')


class ForemanliteCLI(click.MultiCommand):
    """Define MultiCommand CLI that loads from `COMMAND_FOLDER`."""

    def list_commands(self, ctx: Context) -> t.List[str]:
        """
        Get list of command files.
        
        Return
        ------
        list of str
        """

        rv = []
        for filename in os.listdir(COMMAND_FOLDER):
            if filename.endswith('.py') and filename != '__init__.py':
                rv.append(filename.removesuffix('.py'))
        rv.sort()
        return rv
    
    def get_command(self, ctx: Context, cmd_name: str) -> t.Optional[click.Command]:
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

        ns = {}
        fn = os.path.join(COMMAND_FOLDER, cmd_name + '.py')
        with open(fn) as f:
            code = compile(f.read(), fn, 'exec')
            eval(code, ns, ns)
        return ns['cli']


@click.command(cls=ForemanliteCLI)
@click.option('--verbose/--no-verbose', default=False, help='Enable verbose logging')
@click.option('--quiet/--no-quiet', default=False, help='Disable printing logs to screen')
@click.option('--log-file', default='/var/log/foremanlite/foremanlite.log', help='Provide filename to log file')
@click.option('--persist-log/--no-persist-log', default=False, help='Persist logs on disk to given log file. File rotation will be used.')
@click.option('--data-dir', default='/etc/foremanlite/data', help='Path to general purpose data store folder. Mainly used by plugins')
@click.option('--plugin-dir', default='/etc/foremanlite/plugins', help='Path to plugin files.')
@click_config_file.configuration_option()
@click.pass_context
def cli(ctx, verbose, quiet, log_file, persist_log, data_dir, plugin_dir):
    ctx.ensure_obj(dict)
    ctx.obj['DATA_DIR'] = data_dir
    ctx.obj['PLUGIN_DIR'] = plugin_dir
    logging_setup(
        verbose=verbose, 
        use_file=persist_log,
        file_path=log_file,
        use_stream=not quiet,
    )


def run():
    group = ForemanliteCLI(
        help='foremanlite CLI'
    )
    cli()


if __name__ == '__main__':
    run()
