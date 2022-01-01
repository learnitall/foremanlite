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
from foremanlite.fsdata import DataJinjaTemplate
from foremanlite.logging import get as get_logger
from foremanlite.serve.context import get_context
from foremanlite.serve.util import (
    construct_machine_vars,
    handle_template_request,
    machine_parser,
)
from foremanlite.vars import BUTANE_DIR, BUTANE_EXEC, IGNITION_DIR_PATH

ns: Namespace = Namespace("ignition", description="Get ignition config files")
_logger = get_logger("ignition")


@ns.route("/<string:filename>", endpoint="ignition")
@ns.param("filename", "Ignition file to retrieve")
@ns.doc(parser=machine_parser)
class IgnitionFiles(Resource):
    """Resource representing ignition files."""

    @staticmethod
    def get(filename: str):
        """Get the given ignition file and render it."""

        context = get_context()
        ignition_dir_path = context.data_dir / IGNITION_DIR_PATH
        template_factory = lambda path: DataJinjaTemplate(
            path,
            cache=context.cache,
            jinja_render_func=render_template_string,
        )
        return handle_template_request(
            context,
            _logger,
            request,
            filename,
            ignition_dir_path,
            template_factory,
            construct_machine_vars,
        )


@ns.route("/butane/<string:filename>", endpoint="butane")
@ns.param("filename", "Butane file to render")
@ns.doc(parser=machine_parser)
class ButaneFiles(Resource):
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
        template_factory = lambda path: DataButaneFile(
            path,
            butane_exec=butane_exec_path,
            cache=context.cache,
            jinja_render_func=render_template_string,
        )
        return handle_template_request(
            context,
            _logger,
            request,
            filename,
            butane_dir_path,
            template_factory,
            construct_machine_vars,
        )
