#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configure variables for flask startup."""
import typing as t

from flask import Flask
from flask.logging import default_handler

from foremanlite.cli.config import Config
from foremanlite.serve.context import ServeContext, get_context, set_context
from foremanlite.serve.routes import register_blueprints


def start(
    ctx: t.Optional[ServeContext] = None,
    config: t.Optional[Config] = None,
    flask_logging: bool = False,
):
    """
    Start the flask web app for serving client requests.

    One of the below parameters should be given, but if none
    of them are given then no action is performed.

    If both are given, then ctx will be preferred over
    config.

    Parameters
    ----------
    ctx : ServeContext, optional
        Set app's context from a ServeContext instance.
    config : Config, optional
        Set app's context from a Config instance, creating
        a ServeContext using `ServeContext.from_config`.
    flask_logging : boolean, False
        If False, will remove flask's default logging handler
        to prevent duplicate logs, in preference for foremanlite's
        logging setup.
    """

    app = Flask("foremanlite")
    if not flask_logging:
        app.logger.removeHandler(default_handler)

    if ctx is not None:
        set_context(ctx)

    if config is not None:
        set_context(ServeContext.from_config(config))

    context = get_context()

    context.start()
    register_blueprints(app)
    try:
        app.run()
    finally:
        context.stop()
