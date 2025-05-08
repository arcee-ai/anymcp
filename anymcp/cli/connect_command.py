"""
Connect command for anymcp CLI.
"""

import asyncio
import sys
from argparse import ArgumentParser
from typing import Dict, List, Optional

from anymcp import connect_sse_as_stdio
from anymcp.cli import BaseCLICommand
from anymcp.logger import LoggingManager


def connect_command_factory(args):
    """Create a ConnectCommand instance from parsed arguments."""
    return ConnectCommand(
        sse_url=args.sse_url,
        timeout=args.timeout,
        sse_read_timeout=args.sse_read_timeout,
        headers=args.header,
        debug=args.debug,
        token=args.token,
    )


class ConnectCommand(BaseCLICommand):
    """Command to connect to an SSE MCP server and provide stdio interface."""

    @staticmethod
    def register_subcommand(parser: ArgumentParser):
        """Register the connect subcommand with the argument parser."""
        connect_parser = parser.add_parser(
            "connect",
            help="Connect to an SSE MCP server and provide stdio interface",
            description="✨ Connect to an SSE MCP server and provide a stdio interface",
        )
        connect_parser.add_argument("sse_url", help="URL of the SSE endpoint (e.g., http://localhost:8000/sse)")
        connect_parser.add_argument(
            "--timeout", type=float, default=5.0, help="Timeout for HTTP requests (default: 5.0 seconds)"
        )
        connect_parser.add_argument(
            "--sse-read-timeout",
            type=float,
            default=300.0,
            help="Timeout for SSE message reading (default: 300.0 seconds)",
        )
        connect_parser.add_argument(
            "--header", action="append", help="Additional HTTP headers for requests (format: KEY=VALUE)"
        )
        connect_parser.add_argument("--token", help="Authorization bearer token")
        connect_parser.add_argument("--debug", action="store_true", help="Enable debug mode")
        connect_parser.set_defaults(func=connect_command_factory)

    def __init__(
        self,
        sse_url: str,
        timeout: float = 5.0,
        sse_read_timeout: float = 300.0,
        headers: Optional[List[str]] = None,
        debug: bool = False,
        token: Optional[str] = None,
    ):
        """Initialize the connect command."""
        super().__init__()
        self.sse_url = sse_url
        self.timeout = timeout
        self.sse_read_timeout = sse_read_timeout
        self.headers = headers
        self.debug = debug
        self.token = token

        # Set debug level if requested
        if debug:
            LoggingManager.set_level("DEBUG")
            self.logger.debug("Debug logging enabled for connect command")

        self.logger.debug(
            f"Connect command initialized with URL: {sse_url}, timeout: {timeout}, "
            f"SSE read timeout: {sse_read_timeout}"
        )
        if token:
            self.logger.debug("Authorization bearer token provided")

    def run(self):
        """Execute the connect command."""
        self.logger.info(f"Running connect command for SSE server: {self.sse_url}")
        try:
            asyncio.run(self._run_client())
        except KeyboardInterrupt:
            self.logger.info("Connection closed by user")
            print("\nConnection closed by user", file=sys.stderr)
            sys.exit(0)
        except Exception as e:
            self.logger.exception(f"Connection failed: {e}")
            print(f"\nConnection failed: {e}", file=sys.stderr)
            sys.exit(1)

    async def _run_client(self):
        """Run the client asynchronously."""
        # Configure logging
        if self.debug:
            self.logger.debug("Setting up client with debug logging")

        # Parse headers
        headers_dict: Dict[str, str] = {}
        if self.headers:
            for header in self.headers:
                if "=" in header:
                    key, value = header.split("=", 1)
                    headers_dict[key] = value
                    self.logger.debug(f"Added header: {key}={value}")

        # Add authorization header if token is provided
        if self.token:
            headers_dict["Authorization"] = f"Bearer {self.token}"
            self.logger.debug("Added authorization bearer token to headers")

        self.logger.info(f"Connecting to SSE server: {self.sse_url}")
        print(f"Connecting to SSE server: {self.sse_url}", file=sys.stderr)
        print("Press Ctrl+C to exit", file=sys.stderr)

        try:
            self.logger.debug("Establishing connection to SSE server")
            async with connect_sse_as_stdio(
                sse_url=self.sse_url,
                headers=headers_dict,
                timeout=self.timeout,
                sse_read_timeout=self.sse_read_timeout,
                token=self.token,
            ):
                self.logger.info("Connection established successfully")
                # Wait forever (or until Ctrl+C)
                try:
                    self.logger.debug("Entering keep-alive loop")
                    while True:
                        await asyncio.sleep(3600)
                except (asyncio.CancelledError, KeyboardInterrupt):
                    self.logger.info("Connection canceled by user")
                    pass
        except Exception as e:
            self.logger.exception(f"Error in client connection: {e}")
            raise
