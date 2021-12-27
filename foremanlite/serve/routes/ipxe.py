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

from flask import make_response, request
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
    IPXE_BOOT,
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

    Adds the following variables:

    * passfile: filename of the ipxe passthrough file, which boots
      the machine to disk
    * provisionfile: filename of the ipxe provision file, which
      provisions the machine
    * startfile: filename of the ipxe initial boot file, which
      kicks-off pxe booting the machine by chaining the
      appropriate ipxe file
    """

    # Provision by default
    machine = kwargs.get("machine", None)
    if machine is not None and machine.provision is None:
        machine.provision = True
        kwargs["machine"] = machine

    template_vars = {
        "passfile": IPXE_PASSTHROUGH.removesuffix(".j2"),
        "provisionfile": IPXE_PROVISION.removesuffix(".j2"),
        "startfile": IPXE_START.removesuffix(".j2"),
    }

    if machine is not None and kwargs.get("groups", None) is not None:
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


@ns.route(f"/{IPXE_BOOT.removesuffix('.j2')}", endpoint="ipxeboot")
class IPXEBoot(Resource):
    """Resource representing the iPXE initial boot file."""

    @staticmethod
    def get():
        """Render and serve the iPXE boot file."""

        context = get_context()
        ipxe_dir_path = context.data_dir / IPXE_DIR
        resolved_fn = ipxe_dir_path / IPXE_BOOT
        _logger.info(f"Got request for boot file ({str(resolved_fn)})")
        template_vars = _construct_vars_func()
        try:
            resp = make_response(
                DataJinjaTemplate(
                    resolved_fn,
                    cache=context.cache,
                    jinja_render_func=render_template_string,
                ).render(**template_vars),
                200,
            )
            resp.headers["Content-Type"] = "text/plain"
            return resp
        except ValueError as err:
            _logger.warning(
                "Error occurred while rendering boot file "
                f"{str(resolved_fn)} with vars {template_vars}: "
                f"{err}"
            )
            raise err
