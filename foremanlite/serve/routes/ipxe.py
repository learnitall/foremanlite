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
from flask import request, url_for
from flask.templating import render_template_string
from flask_restx import Namespace, Resource

from foremanlite.fsdata import DataJinjaTemplate
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


@ns.route("/<string:filename>", endpoint="ipxefiles")
@ns.param("filename", "Filename of iPXE file to retrieve")
@ns.doc(parser=machine_parser)
class IPXEFiles(Resource):
    """Resource representing iPXE files."""

    @staticmethod
    def get(filename: str):
        """Get the requested iPXE file."""

        endpoint = "ipxefiles"  # constant for convenience
        context = get_context()
        ipxe_dir_path = context.data_dir / IPXE_DIR
        resolved_fn = resolve_filename(filename, ipxe_dir_path)
        if resolved_fn is None:
            return ("Requested iPXE file not found", 404)

        _logger.debug(
            f"Resolved requested filename {filename} to {str(resolved_fn)}"
        )

        # Now we need to determine what machine is making the
        # request, so we can determine if needs to be provisioned
        # or any variables that are needed to do the render
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

        _logger.info(f"Got request from machine {machine}: {str(resolved_fn)}")
        groups = filter_groups(machine, context.groups)
        _logger.info(f"Found groups for {machine}: {groups}")

        # Determine chain target url
        extra_vars = {}
        if resolved_fn == ipxe_dir_path / IPXE_START:
            if machine.provision or machine.provision is None:
                chain_target = IPXE_PROVISION
            else:
                chain_target = IPXE_PASSTHROUGH
            extra_vars["chain_url"] = url_for(
                endpoint, filename=chain_target, _external=True
            )

        template_vars = construct_vars(machine, groups)
        template_vars.update(extra_vars)
        try:
            content = DataJinjaTemplate(
                resolved_fn,
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
