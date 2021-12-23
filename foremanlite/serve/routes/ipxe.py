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

from flask import request, url_for
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
from foremanlite.vars import (
    IPXE_DIR,
    IPXE_PASSTHROUGH,
    IPXE_PROVISION,
    IPXE_START,
)

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

    Adds the `chain_url` variable when rendering IPXE_START,
    representing the next chain url for machines.
    """

    machine = kwargs["machine"]
    resolved_fn = kwargs["resolved_fn"]
    template_vars = {}
    if (resolved_fn).endswith(IPXE_START):
        if machine.provision or machine.provision is None:
            start_chain_target = IPXE_PROVISION
        else:
            start_chain_target = IPXE_PASSTHROUGH
        template_vars["chain_url"] = url_for(
            "ipxefiles", filename=start_chain_target, _external=True
        )

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
