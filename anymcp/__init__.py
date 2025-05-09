"""
AnyMCP - An adapter library for Model Context Protocol (MCP) servers.
"""

__version__ = "0.0.3"

from .logger import LoggingManager, get_logger, logger
from .sse_to_stdio import connect_sse_as_stdio

__all__ = ["connect_sse_as_stdio", "logger", "get_logger", "LoggingManager"]
