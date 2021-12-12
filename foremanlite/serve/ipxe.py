#!/usr/bin/env python3
# -*- coding: utf -8 -*-
"""iPXE API endpoint"""
from flask_restx import Namespace, Resource
import flask_restx


ns = Namespace('ipxe', description='Get iPXE files for provisioning machines')


@ns.route('<string:fn>')
@ns.param('fn', 'Filename to retrieve')
class IPXEFiles(Resource):
    """Resource representing iPXE files."""

    def get(self, fn: str):
        """Get the given iPXE file."""

