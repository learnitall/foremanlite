#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pylint: disable=all
"""
Required configuration of gunicorn for foremanlite.

These settings are required for gunicorn to run properly as
foremanlite's http server.

For more information, see foremanlite.serve.context and
foremanlite.serve.app
"""
import sys

from gunicorn.arbiter import Arbiter
from gunicorn.workers.base import Worker

from foremanlite.logging import FORMAT, ROTATING_FILE_HANDLER_OPTS
from foremanlite.serve.context import ServeContext

# --- Preflight check for needed context variable
_ctx: ServeContext = globals().get("ctx", None)
if _ctx is None:
    raise ValueError("Unable to get current application context.")


# --- Logging setup ---
_handlers_def = {
    "console": {
        "class": "logging.StreamHandler",
        "formatter": "generic",
        "stream": sys.stdout,
    }
}
_handlers_access = ["console"]
_handlers_error = ["console"]
if _ctx.config.persist_log:
    _accesslog_file = f"{_ctx.log_dir}/gunicorn.access.log"
    _errorlog_file = f"{_ctx.log_dir}/gunicorn.error.log"
    _handlers_access.append("accesslog_file")
    _handlers_error.append("errorlog_file")
    _handlers_def["accesslog_file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "formatter": "generic",
        "filename": _accesslog_file,
        **ROTATING_FILE_HANDLER_OPTS,
    }
    _handlers_def["errorlog_file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "formatter": "generic",
        "filename": _errorlog_file,
        **ROTATING_FILE_HANDLER_OPTS,
    }

if _ctx.config.verbose:
    _log_level = "DEBUG"
else:
    _log_level = "INFO"


logconfig_dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "loggers": {
        "gunicorn.access": {
            "level": _log_level,
            "formatter": "generic",
            "handlers": _handlers_access,
        },
        "gunicorn.error": {
            "level": _log_level,
            "formatter": "generic",
            "handlers": _handlers_error,
        },
    },
    "handlers": _handlers_def,
    "formatters": {
        "generic": {"format": FORMAT, "class": "logging.Formatter"}
    },
}


def post_fork(server: Arbiter, worker: Worker):
    """
    After a worker is created, kick-off the `ServeContext` instance.

    This is needed because each worker needs to run `ServerContext.start`,
    otherwise the `ServeContext` it will have will be uninitialized.

    For more information see
    https://docs.gunicorn.org/en/stable/settings.html#post-fork
    """

    _ctx.start()


def worker_exit(server: Arbiter, worker: Worker):
    """
    Before a worker is exited, clean up its `ServeContext` instance.

    For more information see 
    https://docs.gunicorn.org/en/stable/settings.html#worker-exit
    """

    _ctx.stop()
