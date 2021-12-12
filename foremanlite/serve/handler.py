#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Definition of an handler ABC that Resources use to answer requests."""
from abc import ABC, abstractmethod
import typing as t
from dataclasses import dataclass
from flask.wrappers import Request


@dataclass
class Context:
    """Information about a request given to handlers """

    method: str
    request: Request
    handlerSignals: dict[str, t.Any]


class Handler(ABC):
    """Handle requests for a route."""

    @abstractmethod
    def handle(self, ctx: Context) -> Context:
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
    

def add_signal(ctx: Context, handlerClass: t.Type[Handler], data: t.Any):
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

    ctx.handlerSignals[str(handlerClass)] = data

def has_signal(ctx: Context, handlerClass: t.Type[Handler]) -> t.Optional[t.Any]:
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

    return ctx.handlerSignals.get(str(handlerClass), None)


class HandlerChain(Handler):
    """
    Create chain of handlers.

    Context returned by each Handler is passed onto the next.

    Parameters
    ----------
    handlers : list of Handler
        List of handlers to construct chain from.
        Chain executes from first to last in the list.

    Attributes
    ----------
    chain : list of Handler
        List of handlers that are execute from first to last.
        Modify this list to modify the chain.
    """

    def __init__(self, handlers: t.List[Handler]):
        self.chain = handlers
    
    def handle(self, ctx: Context) -> Context:
        for handler in self.chain:
            ctx = handler.handle(ctx)
        return ctx
