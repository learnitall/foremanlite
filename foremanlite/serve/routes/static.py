#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Static file API endpoint.

Used for storing data such as img files.
Nothing in the static directory will be treated as a template,
just (potentially) cacheable data that needs to be served to clients.
"""
from flask import make_response
from flask_restx import Namespace, Resource

from foremanlite.fsdata import DataFile
from foremanlite.logging import get as get_logger
from foremanlite.serve.context import get_context
from foremanlite.vars import STATIC_DIR

ns: Namespace = Namespace(
    "static", description="Get static files as needed for misc. uses."
)
_logger = get_logger("static")


@ns.route("/<string:filename>", endpoint="staticfiles")
@ns.param("filename", "Filename of static file to retrieve")
class StaticFiles(Resource):
    """Resource representing static files."""

    @staticmethod
    def get(filename: str):
        """Get the requested static file."""

        context = get_context()
        static_dir_path = context.data_dir / STATIC_DIR
        requested_path = static_dir_path / filename
        _logger.info(f"Got request for static file ({str(requested_path)})")
        try:
            resp = make_response(
                DataFile(
                    requested_path,
                    cache=context.cache,
                )
                .read()
                .decode("utf-8"),
                200,
            )
            resp.headers["Content-Type"] = "text/plain"
            return resp
        except ValueError as err:
            _logger.warning(
                "Error occurred while reading static file "
                f"{str(requested_path)}: {err}"
            )
            raise err
