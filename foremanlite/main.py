#!/usr/bin/env python3 -m flask
# -*- coding: utf-8 -*-
"""Start the main http web server to start serving requests."""
import logging
from flask import Flask
from foremanlite.classes.routes import construct_route, HelloWorldRouteHandler, BootRouteHandler, StartRouteHandler

app = Flask(__name__)

# https://pedrofullstack.com/2020/08/14/logs-with-flask-and-gunicorn/
gunicorn_logger = logging.getLogger('gunicorn.error')
app.logger.handlers = gunicorn_logger.handlers
app.logger.setLevel(gunicorn_logger.level)

construct_route(app, HelloWorldRouteHandler)
construct_route(app, BootRouteHandler)
construct_route(app, StartRouteHandler)
