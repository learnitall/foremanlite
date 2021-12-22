#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""General utilities for helping to serve foremanlite requests."""
import typing as t
from dataclasses import asdict
from pathlib import Path

from flask.wrappers import Request
from flask_restx.reqparse import ParseResult, RequestParser

from foremanlite.machine import Arch, Mac, Machine, MachineGroup

machine_parser: RequestParser = RequestParser()
machine_parser.add_argument("mac", type=Mac, required=True)
machine_parser.add_argument("arch", type=Arch, required=True)
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


def resolve_filename(
    requested: str,
    base_path: Path,
) -> t.Optional[Path]:
    """
    Determine the name of the requested file in the cache.

    This is mainly used when working with templates. For instance,
    if a client requests the file 'myfile.txt', but we only
    have 'myfile.txt.j2' in the cache/on disk, we need to actually
    serve to the client the rendered 'myfile.txt.j2' rather than
    trying to read 'myfile.txt'.

    Parameters
    ----------
    requested : str
        Filename or path requested from a client.
    base_path : Path
        Path representing base directory where files are served from the
        relevant endpoint. For instance, if an endpoint serves files
        out of /etc/foremanlite/my_endpoint, and a client wants
        a_dir/a_file, then we need to return
        /etc/foremanlite/my_endpoint/a_dir/a_file

    Returns
    -------
    Path
        Resolved path to the given file.
    None
        The requested filename does not exist and a template for it does
        not exist either.
    """

    requested_path = base_path / requested
    potential_template = base_path / (requested + ".j2")
    if requested_path.exists():
        return requested_path
    if potential_template.exists():
        return potential_template
    return None


def construct_vars(
    machine: Machine, groups: t.Set[MachineGroup]
) -> t.Dict[str, t.Any]:
    """
    Construct list of known variables of the machine and its groups.

    Merges all the group's variables and the machine's attributes
    into the same dictionary.
    """

    result = asdict(machine)
    for group in groups:
        if group.vars is not None:
            result.update(**group.vars)

    return result
