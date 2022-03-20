#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Template file API endpoint.

Used for storing j2 templates which need to be rendered before being
sent off to clients.

The function `foremanlite.serve.util.construct_machine_vars` will be
used to construct the variables used to render templates.
The method `flask.templating.render_template_string` will be used
to actually render the template.
"""
from flask import request
from flask.templating import render_template_string
from flask_restx import Namespace, Resource

from foremanlite.fsdata import DataJinjaTemplate
from foremanlite.logging import get as get_logger
from foremanlite.serve.context import get_context
from foremanlite.serve.util import (
    construct_machine_vars,
    handle_template_request,
    machine_parser,
)
from foremanlite.vars import TEMPLATE_DIR

ns: Namespace = Namespace(
    "templates", description="Render template files as needed for misc. uses."
)
_logger = get_logger("templates")


@ns.route("/<string:filename>", endpoint="templatefiles")
@ns.param("filename", "Filename of template file to render")
@ns.doc(parser=machine_parser)
class TemplateFiles(Resource):
    """Resource representing template files."""

    @staticmethod
    def get(filename: str):
        """Get the requested template file."""

        context = get_context()
        template_dir_path = context.data_dir / TEMPLATE_DIR
        _logger.info(
            f"Got request for template file: {str(filename)} in "
            f"{str(template_dir_path)}"
        )
        template_factory = lambda path: DataJinjaTemplate(
            path,
            cache=context.cache,
            jinja_render_func=render_template_string,
        )

        return handle_template_request(
            context=context,
            logger=_logger,
            request=request,
            filename=filename,
            base_dir=template_dir_path,
            template_factory=template_factory,
            template_vars_renderer=construct_machine_vars,
        )
