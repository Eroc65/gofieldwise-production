"""Shared logging configuration for the platform."""

import logging
import sys


def get_logger(name: str, verbose: bool = False) -> logging.Logger:
    """Return a logger with a consistent format.

    Args:
        name: The logger name (usually ``__name__`` of the calling module).
        verbose: When *True* set the level to DEBUG; otherwise INFO.

    Returns:
        A configured :class:`logging.Logger` instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    return logger
