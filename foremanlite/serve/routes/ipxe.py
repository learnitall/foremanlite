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
import os
from pathlib import Path

from flask import Blueprint, request
from flask_restx import Api, Resource

from foremanlite.logging import get as get_logger
from foremanlite.machine import Machine
from foremanlite.serve.context import get_context
from foremanlite.serve.util import (
    find_machine_groups,
    find_stored_machine,
    machine_parser,
    parse_machine_from_request,
    repr_request,
    resolve_filename,
    serve_file,
)
from foremanlite.vars import (
    IPXE_DIR,
    IPXE_PASSTHROUGH,
    IPXE_PROVISION,
    IPXE_START,
    VERSION,
)

blueprint: Blueprint = Blueprint("ipxe", __name__)
api = Api(blueprint, version=VERSION)
ns = api.namespace(
    "ipxe", description="Get iPXE files for provisioning machines"
)
_logger = get_logger("ipxe")


@ns.route("/<string:filename>")
@ns.param("filename", "Filename to retrieve")
@api.doc(parser=machine_parser)
class IPXEFiles(Resource):
    """Resource representing iPXE files."""

    @staticmethod
    def get(filename: str):
        """Get the given iPXE file."""

        context = get_context()
        resolved_fn = resolve_filename(
            context, os.path.join(IPXE_DIR, filename)
        )
        if resolved_fn is None:
            return ("File not found", 404)

        try:
            machine_request: Machine = parse_machine_from_request(request)
        except (ValueError, TypeError) as err:
            _logger.warning(
                "Unable to get machine info from request: "
                f"{repr_request(request)}"
            )
            return (f"Unable to handle request: {err}", 500)

        machine_request = find_stored_machine(context, machine_request)
        machine_groups = find_machine_groups(context, machine_request)

        extra_vars = {}
        if resolved_fn == IPXE_START:
            if machine_request.provision or machine_request.provision is None:
                target = IPXE_PROVISION
            else:
                target = IPXE_PASSTHROUGH
            # Inside our templates we use url_for, which adds the /ipxe/
            # prefix, since that is the namespace we are working in
            # In order to properly serve files then, need to translate
            # path on disk to path in url by removing the prefix
            extra_vars["filename"] = Path(target).relative_to(IPXE_DIR)

        return serve_file(
            context,
            resolved_fn,
            _logger,
            machine=machine_request,
            groups=machine_groups,
            extra_vars=extra_vars,
        )
