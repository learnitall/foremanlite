#!/usr/bin/env python3
# -*- coding: utf -8 -*-
"""iPXE API endpoint"""
import typing as t
from dataclasses import asdict

from flask import Blueprint, request
from flask_restx import Api, Resource

from foremanlite.logging import get as get_logger
from foremanlite.machine import Machine
from foremanlite.serve.context import get_context
from foremanlite.serve.util import (
    machine_parser,
    parse_machine_from_request,
    repr_request,
    serve_file,
)
from foremanlite.vars import (
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

        if filename == "boot.ipxe":
            return serve_file(context, IPXE_START, _logger)

        try:
            machine_request: Machine = parse_machine_from_request(request)
        except (ValueError, TypeError):
            _logger.warning(
                "Unable to get machine info from request: "
                f"{repr_request(request)}"
            )
            return serve_file(context, IPXE_PROVISION, _logger)

        if context.store is not None:
            machine_stored = context.store.get(**asdict(machine_request))
            if len(machine_stored) == 1:
                params: t.Dict[str, t.Any] = asdict(machine_request)
                params.update(asdict(machine_stored))
                machine_request = Machine(**params)

        if machine_request.provision or machine_request.provision is None:
            return serve_file(context, IPXE_PROVISION, _logger)
        return serve_file(context, IPXE_PASSTHROUGH, _logger)
