#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configure variables for flask startup."""
import os
import typing as t
from pathlib import Path

import gunicorn.app.base
from flask import Flask
from flask_restx import Api

from foremanlite.cli.config import Config
from foremanlite.logging import BASENAME
from foremanlite.logging import get as get_logger
from foremanlite.serve.context import ServeContext, get_context, set_context
from foremanlite.serve.routes import register_routes
from foremanlite.vars import GUNICORN_REQUIRED_CONFIG, GUNICORN_CONFIG, GUNICORN_DEFAULT_CONFIG, VERSION

_logger = get_logger("app")
_APP: Flask


def get_app() -> Flask:
    """Return the current Flask instance."""

    return _APP


def set_app(app: Flask):
    """Set the current app to the given Flask instance."""

    global _APP
    _APP = app


def setup(
    ctx: t.Optional[ServeContext] = None,
    config: t.Optional[Config] = None,
) -> None:
    """
    Setup the flask web app and context for serving client requests.

    One of the below parameters should be given, but if none
    of them are given then no action is performed.

    If both are given, then ctx will be preferred over
    config.

    To retrieve the configured context and app, use
    `context.get_context` and `app.get_app` respectively

    Parameters
    ----------
    ctx : ServeContext, optional
        Set app's context from a ServeContext instance.
    config : Config, optional
        Set app's context from a Config instance, creating
        a ServeContext using `ServeContext.from_config`.
    """

    # This name cannot be foremanlite.logging.BASENAME
    # Flask restx will use name below as the base
    # logger for the app, which can conflict with our
    # own logging setup.
    app = Flask(BASENAME + "_app")
    api = Api(
        title=BASENAME + "_api",
        version=VERSION,
    )
    register_routes(api)
    api.init_app(app)

    if ctx is not None:
        set_context(ctx)

    if config is not None:
        set_context(ServeContext.from_config(config))

    set_app(app)


class ForemanliteGunicornApp(gunicorn.app.base.BaseApplication):
    """
    Foremanlite BaseApplication for starting gunicorn.

    See https://docs.gunicorn.org/en/stable/custom.html for more info.
    """

    def __init__(
        self, app: Flask, config_files: t.List[Path], ctx: ServeContext
    ):
        self.app = app
        self.config_files = config_files
        self.ctx = ctx
        self.cfg = gunicorn.app.base.Config()
        super().__init__()

    def load_config(self):
        """
        Load configuration from given gunicorn config file.

        Current context will be made available under the 'ctx'
        variable in globals.
        """

        namespace: t.Dict[str, t.Any] = {"ctx": self.ctx}
        for config_file in self.config_files:
            with config_file.open() as config_file_handler:
                code = compile(config_file_handler.read(), config_file, "exec")
                eval(code, namespace, namespace)
        for key, value in namespace.items():
            if key in self.cfg.settings and value is not None:
                self.cfg.set(key.lower(), value)

    def load(self):
        """Return Flask app"""
        return self.app


def start():
    """
    Start the app using gunicorn as the WSGI webserver.

    Be sure to run setup first!
    """

    app = get_app()
    context = get_context()

    is_ok = lambda p: p.exists() and os.access(p, os.R_OK)

    gunicorn_required_config = context.exec_dir / GUNICORN_REQUIRED_CONFIG
    if not is_ok(gunicorn_required_config):
        raise ValueError(
            "Unable to find required gunicorn configuration."
            f"Was expected at {str(gunicorn_required_config)}"
        )
    configs = [gunicorn_required_config]

    gunicorn_default_config = context.exec_dir / GUNICORN_DEFAULT_CONFIG
    default_available = is_ok(gunicorn_default_config)
    if context.config.gunicorn_layer_default:
        if not default_available:
            raise ValueError(
                "Was told to layer default gunicorn config, but default "
                f"config {str(gunicorn_default_config)} could not be "
                "accessed/read"
            )
        configs.append(gunicorn_default_config)

    gunicorn_config = context.exec_dir / GUNICORN_CONFIG
    if not is_ok(gunicorn_config):
        msg = f"Unable to find gunicorn config at {str(gunicorn_config)}"

        if default_available:
            msg += f". Using default at {str(gunicorn_default_config)}."
            _logger.warning(msg)
            if gunicorn_default_config not in configs:
                configs.append(gunicorn_default_config)
        else:
            msg += (
                f" and default {str(gunicorn_default_config)} "
                "is not available."
            )
            raise ValueError(msg)
    else:
        configs.append(gunicorn_config)

    _logger.info(
        "Using gunicorn config files at "
        f"{', '.join([str(c) for c in configs])}"
    )

    ForemanliteGunicornApp(app=app, config_files=configs, ctx=context).run()
