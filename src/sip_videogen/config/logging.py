"""Logging configuration with Rich handler for pretty console output."""

import logging
import sys
from pathlib import Path
from typing import Literal

from rich.logging import RichHandler


def setup_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO",
    log_file: Path | None = None,
) -> logging.Logger:
    """Configure structured logging with Rich handler.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR).
        log_file: Optional path to log file for file logging.

    Returns:
        The configured root logger for the sip_videogen package.
    """
    log_level = getattr(logging, level.upper())

    # Create the package logger
    logger = logging.getLogger("sip_videogen")
    logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler with Rich for pretty output
    console_handler = RichHandler(
        level=log_level,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        show_time=True,
        show_path=False,
        markup=True,
    )
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(file_handler)

    # Prevent propagation to root logger to avoid duplicate messages
    logger.propagate = False

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger for the given module.

    Args:
        name: Module name (e.g., "sip_videogen.agents"). If None, returns
            the root package logger.

    Returns:
        A logger instance for the specified module.
    """
    if name is None:
        return logging.getLogger("sip_videogen")
    return logging.getLogger(name)
