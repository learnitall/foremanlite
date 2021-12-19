#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""General utilities for helping to serve foremanlite requests."""
import logging
import typing as t

from flask.wrappers import Request
from flask_restx.reqparse import ParseResult, RequestParser

from foremanlite.machine import Arch, Mac, Machine
from foremanlite.serve.app import ServeContext

machine_parser: RequestParser = RequestParser()
machine_parser.add_argument("mac", type=Mac, required=True)
machine_parser.add_argument(
    "arch", type=Arch, choices=tuple(a.value for a in Arch), required=True
)
machine_parser.add_argument("provision", type=bool, required=False)
machine_parser.add_argument("name", type=str, required=False)


def parse_machine_from_request(req: Request) -> Machine:
    """
    Given a flask request, return the requesting Machine instance.

    Information about the machine is pulled from the query string.
    Keys in the query string corresspond 1:1 with attribute
    names of a Machine class.

    Parameters
    ----------
    req : Request
        Flask request instance (i.e. from flask import request)

    Returns
    -------
    Machine
        Machine instance representing the calling machine

    Raises
    ------
    ValueError
        if one of the given values in the request is invalid
    TypeError
        if a parameter is missing for the machine

    """

    machine_params: ParseResult = machine_parser.parse_args(req=req)
    return Machine(**machine_params)


def repr_request(req: Request) -> str:
    """
    Get string representation of the given request.

    Can be used for logging a request in case an error occurs.

    Parameters
    ----------
    req: Request
        Flask request instance to log information about

    Returns
    -------
    str
    """

    return f"{req.method} {req.full_path} from {req.remote_addr}"


def serve_file(
    ctx: ServeContext, target: str, logger: logging.Logger
) -> t.Tuple[str, int]:
    """
    Return the given target file using the given Context.

    Parameters
    ----------
    ctx : ServeContext
        ServeContext to pull cache instance from
    target : str
        File to return content of
    logger : logging.Logger
        Logger to send warning messages to if file was unable to
        be served successfully

    Returns
    -------
    (str, int)
        If file was read successfully, will return (content, 200).
        Otherwise, will return (error message, 500)
    """

    try:
        return (ctx.fs_cache.read_file(target).decode("utf-8"), 200)
    except ValueError as err:
        logger.warning(f"Unable to serve {target}: {err}")
        return (f"Unable to serve {target}", 500)
