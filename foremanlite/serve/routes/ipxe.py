#!/usr/bin/env python3
# -*- coding: utf -8 -*-
"""
iPXE API endpoint.

Will serve iPXE files stored in `data/ipxe`.
Anything ending in `.j2` will
be treated as a jinja template. See
`foremanlite.serve.util.render_machine_template` for
information on how templates are handled.
"""
import typing as t

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
from foremanlite.vars import IPXE_DIR, IPXE_PASSTHROUGH, IPXE_PROVISION

ns: Namespace = Namespace(
    "ipxe", description="Get iPXE files for provisioning machines"
)
_logger = get_logger("ipxe")


def _construct_vars_func(
    *_,
    **kwargs,
) -> t.Dict[str, t.Any]:
    """
    Construct variables for templates.

    Adds the following variables:

    * endpoint: endpoint name of the ipxe files route
    * passfile: filename of the ipxe passthrough file, which boots
      the machine to disk
    * provisionfile: filename of the ipxe provision file, which
      provisions the machine
    """

    # Provision by default
    machine = kwargs["machine"]
    if machine.provision is None:
        machine.provision = True
    kwargs["machine"] = machine

    template_vars = {
        "endpoint": "ipxefiles",
        "passfile": IPXE_PASSTHROUGH.removesuffix(".j2"),
        "provisionfile": IPXE_PROVISION.removesuffix(".j2"),
    }

    template_vars.update(construct_machine_vars(**kwargs))
    return template_vars


@ns.route("/<string:filename>", endpoint="ipxefiles")
@ns.param("filename", "Filename of iPXE file to retrieve")
@ns.doc(parser=machine_parser)
class IPXEFiles(Resource):
    """Resource representing iPXE files."""

    @staticmethod
    def get(filename: str):
        """Get the requested iPXE file."""

        context = get_context()
        ipxe_dir_path = context.data_dir / IPXE_DIR
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
            ipxe_dir_path,
            template_factory,
            _construct_vars_func,
        )
