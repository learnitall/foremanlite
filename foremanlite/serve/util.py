#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""General utilities for helping to serve foremanlite requests."""
import typing as t

from flask.wrappers import Request

from foremanlite.machine import Arch, Mac, Machine


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

    Examples
    --------
    >>> my_request_mock = type(
    ... 'request_mock',
    ... tuple(),
    ... {"args": {
    ...     "mac": "11:22:33:44",
    ...     "arch": "x86_64",
    ... }})
    >>> sorted(list(my_request_mock.args.items()))
    [('arch', 'x86_64'), ('mac', '11:22:33:44')]
    >>> from foremanlite.serve.util import parse_machine_from_request
    >>> from foremanlite.machine import Arch
    >>> machine = parse_machine_from_request(my_request_mock)
    >>> machine.mac
    '11:22:33:44'
    >>> machine.arch == Arch.x86_64
    True
    >>> my_request_mock.args["arch"] = "not an arch"
    >>> try:
    ...     parse_machine_from_request(my_request_mock)
    ... except ValueError:
    ...     print("ValueError")
    ValueError
    """

    switch = {
        "mac": lambda k, v: attrs.append((k, Mac(v))),
        "arch": lambda k, v: attrs.append((k, Arch(v))),
        "name": lambda k, v: attrs.append((k, v)),
    }
    attrs: t.List[t.Tuple[str, t.Any]] = []
    for key, value in req.args.items():
        switch.get(key, lambda k, v: v)(key, value)

    return Machine(**dict(attrs))
