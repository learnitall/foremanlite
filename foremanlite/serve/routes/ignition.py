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

from flask import Blueprint, request
from flask_restx import Api
from flask_restx.resource import Resource

from foremanlite.butane import is_butane_file, render_butane_content
from foremanlite.logging import get as get_logger
from foremanlite.machine import Machine
from foremanlite.serve.context import get_context
from foremanlite.serve.util import (
    find_machine_groups,
    find_stored_machine,
    is_template,
    machine_parser,
    parse_machine_from_request,
    repr_request,
    serve_file,
)
from foremanlite.vars import BUTANE_EXEC, VERSION

blueprint: Blueprint = Blueprint("ignition", __name__)
api = Api(blueprint, version=VERSION)
ns = api.namespace("ignition", description="Get ignition config files")
_logger = get_logger("ignition")


@ns.route("/<string:filename>")
@ns.param("filename", "Filename to retreive")
@api.doc(parser=machine_parser)
class IgnitionFiles(Resource):
    """
    Resource representing ignition files.

    All returned content will be in the format of the ignition spec.
    If a butane file is requested and can be found on disk, it will
    be rendered into the ignition spec and returned.
    """

    @staticmethod
    def get(filename: str):
        """Get the given ignition file"""

        context = get_context()

        try:
            machine_request: Machine = parse_machine_from_request(request)
        except (ValueError, TypeError):
            msg = (
                "Unable to get machine info from request: "
                f"{repr_request(request)}"
            )
            _logger.warning(msg)
            return (msg, 500)

        machine_request = find_stored_machine(context, machine_request)

        if is_template(filename):
            machine_groups = find_machine_groups(context, machine_request)
        else:
            machine_groups = None

        result, code = serve_file(
            ctx=context,
            target=filename,
            logger=_logger,
            machine=machine_request,
            groups=machine_groups,
        )

        if code != 200 or not is_butane_file(filename):
            return (result, code)

        try:
            result = render_butane_content(result, BUTANE_EXEC)
        except ValueError as err:
            msg = f"Unable to serve ignition config for {filename}: {err}"
            _logger.warning(msg)
            return (msg, 500)
        else:
            return (result, 200)
