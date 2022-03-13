#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Static file API endpoint.

Used for storing data such as img files.
Nothing in the static directory will be treated as a template,
just (potentially) cacheable data that needs to be served to clients.
"""
from flask import send_from_directory
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
        _logger.info(f"Got request for static file: {str(requested_path)}")
        data_file = DataFile(
            requested_path,
            cache=context.cache,
        )
        try:
            data_file.validate()
        except ValueError as err:
            _logger.warning(
                "Validation failed for requested static file %s: %s",
                repr(str(requested_path)),
                err,
            )
            return ("Requested file cannot be found", 404)

        try:
            return send_from_directory(
                directory=data_file.path.parent,
                path=data_file.path,
                filename=data_file.path.name,
                cache_timeout=0,
            )
        except ValueError as err:
            _logger.warning(
                "Error occurred while reading static file "
                f"{str(requested_path)}: {err}"
            )
            raise err
