#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Endpoint for handling modifying machines in the foremanlite store.

Has essentially the same structure as the CLI command "machines".
"""
import logging
import typing as t

from flask import make_response, request
from flask.wrappers import Request, Response
from flask_restx import Namespace
from flask_restx.resource import Resource

from foremanlite.fsdata import SHA256
from foremanlite.logging import get as get_logger
from foremanlite.machine import Machine, get_uuid
from foremanlite.serve.context import ServeContext, get_context
from foremanlite.serve.util import (
    machine_parser,
    merge_with_store,
    parse_machine_from_request,
    repr_request,
)
from foremanlite.store import BaseMachineStore

ns: Namespace = Namespace(
    "machines", description="Work with machines known to foremanlite."
)
_logger = get_logger("machines")


def _preflight_check_store(
    context: ServeContext, req: Request
) -> BaseMachineStore:
    """
    Check to make sure a store is defined in the context.

    Returns
    -------
    BaseMachineStore
        Current defined store in the context.

    Raises
    ------
    ValueError
        If a store is not defined.
    """

    store: t.Optional[BaseMachineStore] = context.store
    if store is None:
        raise ValueError(
            "Received request to update machine but no store is"
            f"configured: {repr_request(req)}"
        )
    return store


def _preflight_check_machine_exists(
    store: BaseMachineStore, uuid: SHA256, logger: logging.Logger
) -> t.Tuple[t.Optional[Machine], t.Optional[Response]]:
    """
    Check that the given machine exists in the store.

    Returns
    -------
    tuple
        First item is machine in the store, if it exists, else None.
        Second item is a response to send back to the client if
        the machine does not exist in the store.
    """

    response: t.Optional[Response] = None
    known_machine: t.Optional[Machine] = store.get(uuid)
    if known_machine is None:
        logger.warning(
            "Machine with uuid %s could not be found in the store, unable "
            "to update.",
            uuid,
        )
        response = make_response("Machine not found", 404)
    return known_machine, response


def _make_machine_response(machine: Machine):
    """Create a 200 response with json data describing the machine."""

    resp = make_response(machine.json(), 200)
    resp.headers["Content-Type"] = "application/json"
    return resp


@ns.route("/update", endpoint="update_machine")
@ns.doc(parser=machine_parser)
class UpdateMachine(Resource):
    """Endpoint for updating machines through get requests."""

    @staticmethod
    def get():
        """
        Update machine with given parameters.

        If a store is not configured, 500 is returned

        Expects both mac and arch parameters to be given, so the requested
        machine's uuid can be determined. If one or both are not given,
        then 400 is returned.

        Expects the given machine to be in the store already. If the machine
        is not present in the store, then 404 is returned.

        On success, resulting machine json is returned with status 200.
        """

        context = get_context()
        store: BaseMachineStore = _preflight_check_store(context, request)
        requested_machine: Machine = parse_machine_from_request(request)
        requested_machine_uuid = get_uuid(machine=requested_machine)
        _logger.info(
            "Received request to update machine with uuid %s with the "
            "following parameters: %s",
            requested_machine_uuid,
            requested_machine.dict(),
        )
        known_machine: t.Optional[Machine]
        no_known_machine_resp: t.Optional[Response]
        known_machine, no_known_machine_resp = _preflight_check_machine_exists(
            store, requested_machine_uuid, _logger
        )
        if no_known_machine_resp is not None:
            return no_known_machine_resp

        result: Machine = merge_with_store(
            store, requested_machine, known_machine=known_machine
        )
        return _make_machine_response(result)


@ns.route("/add", endpoint="add_machine")
@ns.doc(parser=machine_parser)
class AddMachine(Resource):
    """Endpoint for adding machines through get requests."""

    @staticmethod
    def get():
        """
        Add machine with given parameters.

        Behaves the same as update, except the given machine is not expected
        to be in the store already.

        If a store is not configured, 500 is returned.

        Expects both mac and arch parameters to be given, so the requested
        machine's uuid can be determined. If one or both are not given,
        then 400 is returned.

        On success, added machine json is returned with status 200.
        """

        context = get_context()
        store: BaseMachineStore = _preflight_check_store(context, request)
        requested_machine: Machine = parse_machine_from_request(request)
        _logger.info(
            "Received request to add the following machine to the store: %s",
            requested_machine.json(),
        )

        result: Machine = merge_with_store(store, requested_machine)
        return _make_machine_response(result)
