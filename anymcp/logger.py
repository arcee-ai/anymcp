"""
Custom logger for anymcp package using Loguru.

This module configures a custom logger with colored output, proper formatting,
and multiple log levels.
"""

import os
import sys
from typing import Any, Optional

from loguru import logger as _logger

# Remove default logger
_logger.remove()

# Define log format
_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# Get log level from environment variable or default to INFO
_LOG_LEVEL = os.getenv("ANYMCP_LOG_LEVEL", "INFO").upper()

# Add console handler with custom format
_logger.add(
    sys.stderr,
    format=_LOG_FORMAT,
    level=_LOG_LEVEL,
    colorize=True,
    backtrace=True,
    diagnose=True,
)

# Create a file handler if log file is specified
_LOG_FILE = os.getenv("ANYMCP_LOG_FILE")
if _LOG_FILE:
    _logger.add(
        _LOG_FILE,
        format=_LOG_FORMAT,
        level=_LOG_LEVEL,
        rotation="10 MB",
        retention="1 week",
        compression="zip",
    )


def get_logger(name: str):
    """
    Get a logger instance for the specified module.

    Args:
        name: Module name or logger name

    Returns:
        A configured logger instance
    """
    return _logger.bind(name=name)


# Configure logger specifically for anymcp
logger = get_logger("anymcp")


class LoggingManager:
    """Manager for configuring and controlling logging behavior."""

    @staticmethod
    def set_level(level: str):
        """
        Set the logging level.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        _logger.remove()
        _logger.add(
            sys.stderr,
            format=_LOG_FORMAT,
            level=level.upper(),
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

        # Re-configure file logger if needed
        if _LOG_FILE:
            _logger.add(
                _LOG_FILE,
                format=_LOG_FORMAT,
                level=level.upper(),
                rotation="10 MB",
                retention="1 week",
                compression="zip",
            )

    @staticmethod
    def enable_file_logging(filepath: str, level: Optional[str] = None):
        """
        Enable logging to a file.

        Args:
            filepath: Path to the log file
            level: Logging level for the file (defaults to the same as console)
        """
        _logger.add(
            filepath,
            format=_LOG_FORMAT,
            level=level.upper() if level else _LOG_LEVEL,
            rotation="10 MB",
            retention="1 week",
            compression="zip",
        )

    @staticmethod
    def format_obj(obj: Any) -> str:
        """
        Format an object for readable logging.

        Args:
            obj: Any object to be formatted

        Returns:
            Formatted string representation
        """
        if isinstance(obj, (dict, list, tuple, set)):
            import json

            try:
                return json.dumps(obj, indent=2, default=str)
            except Exception:
                return str(obj)
        return str(obj)


__all__ = ["logger", "get_logger", "LoggingManager"]
