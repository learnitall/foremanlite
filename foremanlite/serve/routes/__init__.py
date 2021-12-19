#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module containing flask routes to load on start."""
import typing as t

from flask import Blueprint, Flask

from foremanlite.serve.routes import ipxe

blueprints: t.Tuple[Blueprint] = (ipxe.blueprint,)


def register_blueprints(app: Flask):
    """Register all of the blueprints within the routes module."""

    for blueprint in blueprints:
        app.register_blueprint(blueprint)
