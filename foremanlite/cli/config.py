#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Describe configuration variables for runtime."""
from dataclasses import dataclass


@dataclass
class Config:
    """Define config variables and help text."""

    verbose: bool = False
    verbose_help: str = "Enable verbose logging"
    quiet: bool = False
    quiet_help: str = "Disable printing logs to screen"
    log_dir: str = "/var/log/foremanlite"
    log_dir_help: str = "Provide path to log directory. File rotation is used."
    persist_log: bool = False
    persist_log_help: str = "Persist logs to disk at given log dir."
    config_dir: str = "/etc/foremanlite"
    config_dir_help: str = "Path to configuration directory."
    redis: bool = True
    redis_help: str = "Use redis to handle tracking machine state."
    redis_url: str = "redis://localhost:6379"
    redis_url_help: str = "Connection URI to Redis server."
    output_gunicorn_logs: bool = True
    output_gunicorn_logs_help: str = "Print gunicorn logs to the screen"
    gunicorn_layer_default: bool = True
    gunicorn_layer_default_help: str = (
        "Layer gunicorn config on top of "
        "the default gunicorn config. This lets user configurations use "
        "and override variables in the gunicorn config."
    )
    max_cache_file_size: int = 10 ** 8
    max_cache_file_size_help: str = (
        "Max file size that will be cached (in bytes)"
    )

    def __hash__(self):
        return hash(repr(self))


DEFAULT_CONFIG = Config()
