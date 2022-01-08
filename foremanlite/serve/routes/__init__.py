#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module containing flask routes to load on start."""
import typing as t

from flask_restx import Api, Namespace

from foremanlite.serve.routes import ignition, ipxe, machines, static

namespaces: t.Tuple[Namespace, ...] = (
    ignition.ns,
    ipxe.ns,
    static.ns,
    machines.ns,
)


def register_routes(api: Api):
    """Register all of the routes within the routes module."""

    for namespace in namespaces:
        api.add_namespace(namespace)
