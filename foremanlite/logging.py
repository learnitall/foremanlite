#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Initialize and configure foremanlite logging."""
import logging
import logging.handlers
import typing as t

BASENAME = "foremanlite"  # Base logger name
# Format of  log messages
FORMAT = "%(asctime)s - %(levelname)s - %(name)s :: %(message)s"
ROTATING_FILE_HANDLER_OPTS: t.Dict[str, t.Any] = {
    "mode": "0644",
    "maxBytes": 500 * (10 ** 6),  # 500 MB
    "backupCount": 5,
}


def get_stream_handler(
    formatter: logging.Formatter, level: int
) -> logging.StreamHandler:
    """
    Create a ready-to-go stream handler for a Logger.

    Parameters
    ----------
    formatter : logging.Formater
        Formatter to apply to the handler.
    level : int
        Level to apply to the stream handler.

    Returns
    -------
    logging.StreamHandler
    """

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler


def get_file_handler(
    formatter: logging.Formatter, level: int, file_path: str
) -> logging.handlers.RotatingFileHandler:
    """
    Create a ready-to-go rotating file handler for a Logger.

    Parameters
    ----------
    formatter : logging.Formatter
        Formatter to apply to the handler
    level : int
        Level to apply to the file handler

    Returns
    -------
    logging.FileHandler
    """

    handler = logging.handlers.RotatingFileHandler(
        file_path, **ROTATING_FILE_HANDLER_OPTS
    )
    handler.setFormatter(formatter)
    handler.setLevel(level)
    return handler


def setup(
    verbose: bool = False,
    use_file: bool = False,
    file_path: str = None,
    use_stream: bool = True,
):
    """
    Populate module-level logger using given options.

    Sets module level LOGGER attribute.

    Parameters
    ----------
    verbose : bool
        If True, sets level to DEBUG. Otherwise, level is set to INFO.
    use_file : bool
        Use a file handler. Created with `get_file_handler`.
    file_path : str
        Set path for file handler. Required if `use_file` is `True`.
    use_stream : bool
        Use a stream handler. Created with `get_stream_handler`.

    Return
    ------
    None

    Raises
    ------
    ValueError
        If `file_path` is not given and `use_file` is `True`.
    """

    formatter = logging.Formatter(FORMAT)
    level = logging.DEBUG if verbose else logging.INFO
    logger = logging.getLogger(BASENAME)
    logger.propagate = False
    logger.setLevel(level)

    if use_file:
        if not isinstance(file_path, str):
            raise ValueError(
                "Expected string for file_path argument, instead got "
                f"{type(file_path)}"
            )

        logger.addHandler(get_file_handler(formatter, level, file_path))

    if use_stream:
        logger.addHandler(get_stream_handler(formatter, level))


def teardown():
    """
    Undo relevant actions performed by `setup`.

    Mainly used for testing purposes. Essentially removes all handlers
    on the logger with `BASENAME`.
    """

    logger = logging.getLogger(BASENAME)
    for handler in logger.handlers:
        logger.removeHandler(handler)


def get(name: str) -> logging.Logger:
    """
    Get a new logger with the given name under the foremanlite namespace.

    Parameters
    ----------
    name : str
        Name of the new logger to get. Should not be prefixed with `BASENAME`.

    Return
    ------
    logging.Logger
    """

    return logging.getLogger(BASENAME).getChild(name)
