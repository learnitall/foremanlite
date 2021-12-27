#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""General utilities for helping to serve foremanlite requests."""
import logging
import typing as t
from dataclasses import asdict
from pathlib import Path

from flask import make_response
from flask.wrappers import Request
from flask_restx.inputs import boolean
from flask_restx.reqparse import ParseResult, RequestParser
from werkzeug.exceptions import BadRequest

from foremanlite.fsdata import DataJinjaTemplate
from foremanlite.machine import Arch, Mac, Machine, MachineGroup, get_uuid
from foremanlite.serve.context import ServeContext
from foremanlite.store import BaseMachineStore

machine_parser: RequestParser = RequestParser()
machine_parser.add_argument("mac", type=Mac, required=True)
machine_parser.add_argument("arch", type=Arch, required=True)
machine_parser.add_argument("provision", type=boolean, required=False)
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


class TemplateVarsRenderCallable(t.Protocol):
    """
    Type definition for a function which renders template variables.

    As a convention, only call functions which implement this signature
    by passing parameters as kwargs. This prevents folks from having
    to type of the entire signature whenever they want to define a
    function with it. Some type checkers don't support just adding in
    a subset of the parameters and taking care of the rest with a
    `*args, **kwargs`.

    For instance, some type checkers may complain at:

    ```
    def my_render_func(machine: Machine, *args, **kwargs):
        ...
    ```

    But they won't complain at:

    ```
    def my_render_func(*_, **kwargs):
        machine = kwargs["machine"]
    ```

    Parameters
    ----------
    context : ServeContext
        Current application's ServeContext instance.
    resolved_fn : Path
        Resolved path to the target file to render.
    request : flask.Request
        flask request instance which is being served
    machine : Machine
        Resolved machine from the request.
    groups : set of MachineGroup
        groups the resolved machine is a part of.
    """

    def __call__(
        self,
        context: ServeContext,
        resolved_fn: Path,
        request: Request,
        machine: Machine,
        groups: t.Set[MachineGroup],
    ) -> t.Dict[str, t.Any]:
        ...


def construct_machine_vars(*_, **kwargs) -> t.Dict[str, t.Any]:
    """
    Construct list of known variables of the machine and its groups.

    Merges all the group's variables and the machine's attributes
    into the same dictionary. Groups will be merged by lexicographical
    order of their name.
    """

    machine = kwargs["machine"]
    groups = kwargs["groups"]
    result = asdict(machine)
    result["arch"] = str(result["arch"].value)
    groups = sorted(groups, key=lambda g: g.name)
    for group in groups:
        if group.vars is not None:
            result.update(**group.vars)

    return result


def merge_with_store(
    store: BaseMachineStore, machine_request: Machine
) -> Machine:
    """
    Check if given machine is in the store.

    If a machine in the store as the same hash as the given machine,
    do nothing and return the given machine.

    If the machine is not in the store, then add it.

    If the machine in the store has a different hash than the given machine,
    then update the machine in the store with the values of the given
    machine and return the result.
    """

    result = store.get(get_uuid(machine=machine_request))
    if result is None:
        machine = machine_request
        store.put(machine)
    elif hash(result) != hash(machine_request):
        merged = asdict(result)
        merged.update(asdict(machine_request))
        merged_machine = Machine(**merged)
        store.put(merged_machine)
        machine = merged_machine
    else:
        machine = result

    return machine


def handle_template_request(
    context: ServeContext,
    logger: logging.Logger,
    request: Request,
    filename: str,
    base_dir: Path,
    template_factory: t.Callable[[Path], DataJinjaTemplate],
    template_vars_renderer: TemplateVarsRenderCallable,
):
    """
    Handler function for routes that server parsable templates.

    Here's the workflow:

    * Resolve requested filename. If this cannot be done, return
      404
    * Parse a machine from a request. If this cannot be done,
      return 400
    * If the store is available, merge the parsed machine with
      machines in the store
    * Find groups the machine belongs to
    * Construct variables for the template.
    * Render and serve the template. If this cannot be done,
      then raise `ValueError`.

    Parameters
    ----------
    context : ServeContext
        Context of the application when request was made.
    logger : logging.Logger
        Logger to send messages to.
    request : flask.Request
        Request instance representing the relevent request to serve.
    filename : str
        Filename of the requested template/file.
    base_dir : Path
        Base directory where the file is served out of.
    template_factory : Callable
        Template factory to use for creating a DataJinjaTemplate instance
        or subclass. First and only argument is path to template which
        needs to be rendered.
    template_vars_renderer : TemplateVarsRenderCallable
        Callable for determining vars for the template.
    """

    resolved_fn = resolve_filename(filename, base_dir)
    if resolved_fn is None:
        return ("Requested file cannot be found", 404)

    logger.debug(
        f"Resolved requested filename {filename} to {str(resolved_fn)}"
    )

    try:
        machine_request: Machine = parse_machine_from_request(request)
    except (ValueError, TypeError, BadRequest) as err:
        logger.warning(
            "Unable to get machine info from request "
            f"{repr_request(request)}: {err}"
        )
        return (f"Unable to handle request: {err}", 400)

    if context.store is not None:
        machine = merge_with_store(context.store, machine_request)
    else:
        machine = machine_request

    logger.info(f"Got request from machine {machine}: {str(resolved_fn)}")

    groups = context.groups.filter(machine)
    if len(groups) > 0:
        logger.info(f"Found groups for {machine}: {groups}")
    else:
        logger.info(f"No groups found for machine {machine}")

    template_vars = template_vars_renderer(
        context=context,
        resolved_fn=resolved_fn,
        request=request,
        machine=machine,
        groups=groups,
    )
    template = template_factory(resolved_fn)
    try:
        resp = make_response(
            template.render(**template_vars),
            200,
        )
        resp.headers["Content-Type"] = "text/plain"
        return resp
    except ValueError as err:
        logger.warning(
            f"Error occurred while rendering {str(resolved_fn)} "
            f"with vars {template_vars}: {err}"
        )
        raise err
