#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tools for working with butane files."""
import subprocess
import typing as t
from pathlib import Path

from foremanlite.fsdata import (
    DataJinjaTemplate,
    FileSystemCache,
    JinjaRenderFuncCallable,
)


class ButaneRenderFuncCallable(t.Protocol):
    """Type definition for butane render function."""

    def __call__(
        self,
        source: str,
        butane_exec: str,
    ) -> str:
        ...


def render_butane_string(
    source: str,
    butane_exec: str,
) -> str:
    """
    Render the given butane template string and return the result.

    Parameters
    ----------
    source : str
        content of butane file to render
    butane_exec : str
        path to butane executable

    Returns
    -------
    str
        ignition file content rendered from given butane file content

    Raises
    ------
    ValueError
        If the butane content could not be rendered
    """

    try:
        proc = subprocess.run(
            butane_exec,
            input=source.encode("utf-8"),
            capture_output=True,
            check=True,
        )
    except subprocess.SubprocessError as err:
        raise ValueError(f"Unable to render butane config {source}: {err}")
    else:
        return proc.stdout.decode("utf-8")


class DataButaneFile(DataJinjaTemplate):
    """
    Representation of a jinja template-able butane file.

    Complies with coreos specification. See
    https://github.com/coreos/butane/blob/main/docs/specs.md
    for more details.

    Parameters
    ----------
    path : Path
        See DataJinjaTemplate.
    butane_exec : Path
        Path to butane executable to render with.
    cache : FileSystemCache, optional
        See DataJinjaTemplate.
    jinja_render_func : JinjaRenderFuncCallable, optional
        See DataJinjaTemplate
    butane_render_func : ButaneRenderFuncCallable, optional
        Function to use in order to render the butane content.
        Defaults to `render_butane_string`. Compatible functions
        take the content of the butane file as the first argument and
        take the path to the butane executable as the second argument.
    """

    def __init__(
        self,
        path: Path,
        butane_exec: Path,
        cache: t.Optional[FileSystemCache] = None,
        jinja_render_func: t.Optional[JinjaRenderFuncCallable] = None,
        butane_render_func: t.Optional[ButaneRenderFuncCallable] = None,
    ):
        super().__init__(
            path=path, cache=cache, jinja_render_func=jinja_render_func
        )

        if butane_render_func is None:
            self._butane_render_func = render_butane_string
        else:
            self._butane_render_func = butane_render_func
        self.butane_exec = butane_exec

    def butane_render_func(self, source: str, butane_exec: str) -> str:
        """
        Pass given args and kwargs to stored butane render function.

        See DataJinjaTemplate for more details.
        """

        return self._butane_render_func(source, butane_exec)

    def render(self, **context: t.Any) -> bytes:
        """
        Read the butane file from disk and render using given variables.

        Will render the file as a jinja template first and then
        as a butane file. See DataJinijaTemplate for more details.
        """

        content: str = super().render(**context).decode("utf-8")
        return self.butane_render_func(content, str(self.butane_exec)).encode(
            "utf-8"
        )
