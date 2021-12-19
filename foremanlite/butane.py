#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tools for working with butane files."""
import subprocess


def is_butane_file(filename: str) -> bool:
    """
    Returns True if given filename represents a butane config file.

    Essentially returns if the filename ends in `.bu`
    """

    return filename.endswith(".bu")


def render_butane_content(content: str, butane_exec: str) -> str:
    """
    Render the given butane template and return the result.

    Parameters
    ----------
    content : str
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
            input=content.encode("utf-8"),
            capture_output=True,
            check=True,
        )
    except subprocess.SubprocessError as err:
        raise ValueError(f"Unable to render butane config {content}: {err}")
    else:
        return proc.stdout.decode("utf-8")
