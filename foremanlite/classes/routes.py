# -*- coding: utf-8 -*-
"""Collection of class-based routes for Flask"""
from abc import ABC
from typing import Type
from collections.abc import Callable
from flask import Flask, render_template
from markupsafe import escape


HandlerMethod = Callable[..., str]


class BaseRouteHandler(ABC):
    """ABC Route Handler to define interface of RouteHandler classes"""
    
    ROUTE: str
    HANDLER: HandlerMethod


class BootRouteHandler(BaseRouteHandler):
    ROUTE: str = "/boot.ipxe"
    
    @classmethod
    def arch(cls) -> str:
        return render_template('boot.ipxe.j2')

    HANDLER: HandlerMethod = arch


class StartRouteHandler(BaseRouteHandler):
    ROUTE: str = "/start/<string:arch>"

    @classmethod
    def start(cls, arch: str):
        return f'Hello {escape(arch)}'
    
    HANDLER: HandlerMethod = start


class HelloWorldRouteHandler(BaseRouteHandler):
    ROUTE: str = "/hello/<string:user>"

    @classmethod
    def hello(cls, user) -> str:
        return f'Hello {escape(user)}!'
    
    HANDLER: HandlerMethod = hello


def construct_route(app: Flask, handler: Type[BaseRouteHandler]):
    """Construct a route on the given app using the given handler."""

    app.route(handler.ROUTE)(handler.HANDLER)
