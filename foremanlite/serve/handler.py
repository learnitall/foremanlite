#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Definition of an handler ABC that Resources use to answer requests."""
import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass

from flask.wrappers import Request


@dataclass
class Context:
    """Information about a request given to handlers"""

    method: str
    request: Request
    handler_signals: t.Dict[str, t.Any]


class Handler(ABC):
    """Handle requests for a route."""

    @abstractmethod
    def handle(self, ctx: Context) -> t.Any:
        """
        Handle the given request.

        Parameters
        ----------
        ctx : Context
            Context used to pull relevant information regarding the request

        Returns
        -------
        Context
            Passthrough (Un)modified context object.
        """


def add_signal(ctx: Context, handler_class: t.Type[Handler], data: t.Any):
    """
    Add signal for a handlerClass in a context.

    Paremeters
    ----------
    ctx : Context
        Context to add signal into.
    handlerClass : Handler class
        Handler class to set signal for. Should be subclass of Handler ABC
    data : Any
        Data to provide in signal.
    """

    ctx.handler_signals[str(handler_class)] = data


def has_signal(
    ctx: Context, handler_class: t.Type[Handler]
) -> t.Optional[t.Any]:
    """
    Return signal for handler in context.

    Paremeters
    ----------
    ctx : Context
        Context to check for signal
    handlerClass : Handler class
        Handler class to return signal for. Should be sublass of Handler ABC

    Returns
    -------
    None
        If no signal for given handler was found
    Any
        Data for the handler put into the signal
    """

    return ctx.handler_signals.get(str(handler_class), None)
