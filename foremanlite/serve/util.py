#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""General utilities for helping to serve foremanlite requests."""
import logging
import typing as t
from dataclasses import asdict

from flask import render_template_string
from flask.wrappers import Request
from flask_restx.reqparse import ParseResult, RequestParser

from foremanlite.machine import Arch, Mac, Machine, MachineGroup
from foremanlite.serve.app import ServeContext

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


def is_template(filename: str) -> bool:
    """Return wether or not the given file is a template."""

    return filename.endswith(".j2")


def resolve_filename(
    ctx: ServeContext,
    requested: str,
) -> t.Optional[str]:
    """
    Determine the name of the requested file in the cache.

    This is mainly used when working with templates. For instance,
    if a client requests the file 'myfile.txt', but we only
    have 'myfile.txt.j2' in the cache/on disk, we need to actually
    serve to the client the rendered 'myfile.txt.j2' rather than
    trying to read 'myfile.txt'.

    Parameters
    ----------
    ctx : ServeContext
        ServeContext instance to get cache and other runtime variables from.
    requested : str
        Filename requested from a client.

    Returns
    -------
    str
        Equivalent name of the requested file within the cache. This
        will either be the requested filename if it exists, or the
        filename of the associated template.
    None
        The requested filename does not exist and a template for it does
        not exist either.
    """

    template = requested + ".j2"
    if ctx.fs_cache.file_exists(requested):
        return requested
    if ctx.fs_cache.file_exists(template):
        return template
    return None


def render_machine_template(
    ctx: ServeContext,
    target: str,
    machine: t.Optional[Machine] = None,
    groups: t.Optional[t.Set[MachineGroup]] = None,
    extra_vars: t.Optional[t.Dict[str, t.Any]] = None,
) -> str:
    """
    Render jinja template pulling vars from given machine and groups.

    Parameters
    ----------
    ctx : ServeContext
        Context to use while rendering the template
    target : str
        Name of jinja template to render. Will be pulled
        using context's fs_cache.
    machine : Machine, optional
        Machine whose's attributes will be made available
        as variables in the jinja template. Access to these
        attributes is available under the 'machine' key.
    groups : set of MachineGroup, optional
        Optional set of MachineGroup instances to pass
        whose variables will be made available to the template.
        Access to these variables is available under the
        'groups' key, with each group's key being its
        configured name.
    extra_vars : dict, optional
        Additional variables to expose to the template.
        These will be made available under the 'vars' key.

    Returns
    -------
    str
        Content of rendered template
    """

    content = ctx.fs_cache.read_file(target).decode("utf-8")
    return render_template_string(
        content, machine=machine, groups=groups, vars=extra_vars
    )


def serve_file(
    ctx: ServeContext,
    target: str,
    logger: logging.Logger,
    machine: t.Optional[Machine] = None,
    groups: t.Optional[t.Set[MachineGroup]] = None,
    extra_vars: t.Optional[t.Dict[str, t.Any]] = None,
) -> t.Tuple[str, int]:
    """
    Return the given target file using the given Context.

    For more information on how templates are rendered,
    see `render_machine_template`. Parameters to this
    function are coupled with `render_machine_template`'s
    parameters.

    Parameters
    ----------
    ctx : ServeContext
        ServeContext to pull cache instance from
    target : str
        File to return content of.
    logger : logging.Logger
        Logger to send warning messages to if file was unable to
        be served successfully
    machine : Machine, optional
        Machine to expose to template for rendering.
    groups : set of MachineGroup, optional
        Set of MachineGroups to expose to template for rendering
    extra_vars : dict, optional
        Additional vars to be made available to the template.

    Returns
    -------
    (str, int)
        If file was read successfully, will return (content, 200).
        Otherwise, will return (error message, 500)
    """

    err_msg: str = ""
    content: str = ""
    success: bool = False
    if is_template(target):
        try:
            content = render_machine_template(
                ctx=ctx,
                target=target,
                machine=machine,
                groups=groups,
                extra_vars=extra_vars,
            )
        except ValueError as err:
            err_msg = f"Unable to render or serve template at {target}: {err}"
        else:
            success = True
    else:
        try:
            content = ctx.fs_cache.read_file(target).decode("utf-8")
        except ValueError as err:
            err_msg = f"Unable to serve file {target}: {err}"
        else:
            success = True

    if success:
        return (content, 200)

    logger.warning(err_msg)
    return (err_msg, 500)


def find_machine_groups(
    ctx: ServeContext, machine: Machine
) -> t.Set[MachineGroup]:
    """Get MachineGroup instances which the given Machine belongs to."""

    if ctx.groups is None:
        return set()
    return {group for group in ctx.groups if group.matches(machine)}


def find_stored_machine(
    ctx: ServeContext, machine: Machine, add_if_missing: bool = False
) -> Machine:
    """
    Find matching machine in store for the given machine.

    If `add_if_missing` is given, then the given machine
    will be added into the context's store if the machine
    was not present.

    Returns
    -------
    Machine
        If a match is found, a new Machine is returned with
        the combined attributes of the given machine and the
        machine in the store. Otherwise the given machine
        is returned.
    """

    if ctx.store is not None:
        params = asdict(machine)
        stored = ctx.store.get(**params)
        if len(stored) == 1:  # exact match
            params.update(asdict(stored))
            return Machine(**params)
        if add_if_missing:
            ctx.store.put(machine)

    return machine
