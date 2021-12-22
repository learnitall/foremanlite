#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ignition endpoint to serve ignition configs to machines.

Ignition configurations are expected to be stored
as ignition files (`.ign`) or butane files (`.bu`)
within `data/ignition`. Anything ending in `.j2` will
be treated as a jinja template. See
`foremanlite.serve.util.render_machine_template` for
information on how templates are handled.
"""
from flask import render_template_string, request
from flask_restx import Namespace
from flask_restx.resource import Resource

from foremanlite.butane import DataButaneFile
from foremanlite.logging import get as get_logger
from foremanlite.machine import Machine, filter_groups
from foremanlite.serve.context import get_context
from foremanlite.serve.util import (
    construct_vars,
    machine_parser,
    merge_with_store,
    parse_machine_from_request,
    repr_request,
    resolve_filename,
)
from foremanlite.vars import BUTANE_DIR, BUTANE_EXEC

ns: Namespace = Namespace("ignition", description="Get ignition config files")
_logger = get_logger("ignition")


@ns.route("/butane/<string:filename>", endpoint="butane")
@ns.param("filename", "Butane file to render")
@ns.doc(parser=machine_parser)
class IgnitionFiles(Resource):
    """
    Resource representing renderable butane files.

    All returned content will be in the format of the ignition spec.
    """

    @staticmethod
    def get(filename: str):
        """Get the given butane file and render it."""

        context = get_context()
        butane_dir_path = context.data_dir / BUTANE_DIR
        butane_exec_path = context.exec_dir / BUTANE_EXEC
        resolved_fn = resolve_filename(filename, butane_dir_path)
        if resolved_fn is None:
            return ("Requested butane file not found", 404)

        # Determine what machine is making the request, so
        # we know which variables to pass to the butane
        # template
        try:
            machine_request: Machine = parse_machine_from_request(request)
        except (ValueError, TypeError) as err:
            _logger.warning(
                "Unable to get machine info from request: "
                f"{repr_request(request)}"
            )
            return (f"Unable to handle request: {err}", 400)

        # check if the requested machine is known
        if context.store is not None:
            machine = merge_with_store(context.store, machine_request)
        else:
            machine = machine_request

        _logger.info(
            f"Got request from machine {machine} for {str(resolved_fn)}"
        )
        groups = filter_groups(machine, context.groups)
        _logger.info(f"Found groups for machine {machine}: {groups}")
        template_vars = construct_vars(machine, groups)

        try:
            content = DataButaneFile(
                resolved_fn,
                butane_exec=butane_exec_path,
                cache=context.cache,
                jinja_render_func=render_template_string,
            )
            return (content.render(**template_vars).decode("utf-8"), 200)
        except ValueError as err:
            _logger.warning(
                f"Error occurred while rendering {str(resolved_fn)} "
                f"with vars {template_vars}: {err}"
            )
            raise err
