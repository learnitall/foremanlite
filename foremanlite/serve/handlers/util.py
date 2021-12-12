#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Common handlers for basic functionality."""
import typing as t
from flask.templating import render_template_string
from foremanlite.serve.handler import Handler, Context, has_signal
from foremanlite.store import get_cache




class FileSystemHandler(Handler):
    """Handle reading files from the FS."""

    def handle(self, ctx: Context) -> t.Any:
        entry = has_signal(ctx, __class__)
        if entry is not None:
            cache = get_cache()
            if cache is not None:
                return cache.read_file(entry)


class TemplateHandler(Handler):
    """Serve templates from the filesystem."""

    @staticmethod
    def render_template(template: str, **kwargs) -> str:
        """
        Render the given template using the given args and kwargs.

        Parameters
        ----------
        template : str

        Returns
        -------
        str
        """

        return render_template_string(template, **kwargs)
    
    def handle(self, ctx: Context) -> t.Any:
        entry = has_signal(ctx, __class__)
        if entry is not None:
            cache = get_cache()
            if cache is not None:
                return self.render_template(
                    cache.read_file(entry).decode('utf-8')
                )