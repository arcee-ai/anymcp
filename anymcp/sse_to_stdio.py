#!/usr/bin/env python
"""
Bridge an SSE-based MCP server to stdio.
"""
import argparse
import asyncio
import contextlib
import os.path
import sys
import time
from typing import AsyncIterator, Dict, Optional, Tuple
from urllib.parse import ParseResult, urlparse

import anyio
import httpx
from httpx_sse import aconnect_sse
from mcp.server.stdio import stdio_server

from anymcp.logger import LoggingManager, get_logger

# Configure logger for this module
logger = get_logger("anymcp.sse-to-stdio")


@contextlib.asynccontextmanager
async def connect_sse_as_stdio(
    sse_url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 5.0,
    sse_read_timeout: float = 300.0,
    token: Optional[str] = None,
) -> AsyncIterator[Tuple]:
    """
    Connect to an SSE-based MCP server and bridge it to stdio.

    Args:
        sse_url: The URL of the SSE server (e.g., http://localhost:8000/sse)
        headers: Additional HTTP headers to send with the request
        timeout: HTTP request timeout in seconds
        sse_read_timeout: SSE read timeout in seconds
        token: Authorization bearer token

    Returns:
        A tuple of (reader, writer) for communicating with the bridged server
    """
    if headers is None:
        headers = {}

    # Add authorization header if token is provided
    if token:
        headers["Authorization"] = f"Bearer {token}"
        logger.debug("Added authorization bearer token to headers")

    # Ensure proper content type for SSE connection
    headers["Content-Type"] = "text/event-stream"
    headers["Cache-Control"] = "no-cache"
    headers["Connection"] = "keep-alive"
    headers["Accept"] = "text/event-stream"

    logger.debug("Added connection headers for SSE connection")

    logger.info(f"Starting bridge for SSE server: {sse_url}")
    logger.debug(f"Connection parameters: timeout={timeout}s, sse_read_timeout={sse_read_timeout}s")
    if headers:
        logger.debug(f"Using {len(headers)} HTTP headers")

    # Extract base path from the SSE URL to use for the message endpoint
    parsed_url = urlparse(sse_url)
    base_path = os.path.dirname(parsed_url.path)
    if not base_path.endswith("/"):
        base_path += "/"
    logger.debug(f"Extracted base path from SSE URL: {base_path}")

    # Connect to the SSE server with a custom wrapper that fixes message endpoint paths
    logger.debug(f"Connecting to SSE endpoint at {sse_url}")
    async with _wrapped_sse_client(
        url=sse_url,
        base_path=base_path,
        headers=headers,
        timeout=timeout,
        sse_read_timeout=sse_read_timeout,
    ) as (sse_read, sse_write):
        logger.info("Connected to SSE server")

        # Create stdio server
        logger.debug("Setting up stdio server interface")
        async with stdio_server() as (stdio_read, stdio_write):
            logger.info("Stdio interface ready")

            # Create bridge between the two
            logger.debug("Creating bidirectional bridge between SSE and stdio")
            async with anyio.create_task_group() as tg:
                # Forward messages from SSE to stdio
                async def forward_sse_to_stdio():
                    msg_count = 0
                    try:
                        async with sse_read:
                            logger.debug("Starting SSE → stdio message forwarding")
                            async for message in sse_read:
                                if isinstance(message, Exception):
                                    logger.error(f"Error from SSE: {message}")
                                    continue

                                msg_count += 1
                                logger.debug(f"Forwarding from SSE to stdio: {message}")
                                if msg_count % 100 == 0:
                                    logger.info(f"Forwarded {msg_count} messages from SSE to stdio")
                                await stdio_write.send(message)
                    except Exception as e:
                        logger.exception(f"Error in SSE->stdio bridge: {e}")

                # Forward messages from stdio to SSE
                async def forward_stdio_to_sse():
                    msg_count = 0
                    try:
                        async with stdio_read:
                            logger.debug("Starting stdio → SSE message forwarding")
                            async for message in stdio_read:
                                if isinstance(message, Exception):
                                    logger.error(f"Error from stdio: {message}")
                                    continue

                                msg_count += 1
                                logger.debug(f"Forwarding from stdio to SSE: {message}")
                                if msg_count % 100 == 0:
                                    logger.info(f"Forwarded {msg_count} messages from stdio to SSE")
                                await sse_write.send(message)
                    except Exception as e:
                        logger.exception(f"Error in stdio->SSE bridge: {e}")

                # Start forwarding in both directions
                logger.debug("Starting bidirectional message forwarding")
                tg.start_soon(forward_sse_to_stdio)
                tg.start_soon(forward_stdio_to_sse)

                # Yield so the caller can use the bridged connection
                logger.debug("SSE-stdio bridge established and running")
                yield (stdio_read, stdio_write)
                logger.debug("SSE-stdio bridge connection context closed")


@contextlib.asynccontextmanager
async def _wrapped_sse_client(
    url: str,
    base_path: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 5.0,
    sse_read_timeout: float = 300.0,
):
    """
    Wrapper around the standard SSE client that ensures message endpoint URLs
    use the correct base path.

    Args:
        url: The URL of the SSE server
        base_path: The base path to prepend to message endpoints
        headers: Additional HTTP headers to send with the request
        timeout: HTTP request timeout in seconds
        sse_read_timeout: SSE read timeout in seconds
    """
    # Create a wrapper around the original sse_client
    logger.debug(f"Wrapping SSE client with base_path={base_path}")

    # Parse URL to get the base components
    parsed_url = urlparse(url)

    # Create memory streams for our custom client
    read_stream_writer, read_stream = anyio.create_memory_object_stream(0)
    write_stream, write_stream_reader = anyio.create_memory_object_stream(0)

    # Function to fix endpoint URLs
    def fix_endpoint_url(endpoint_url):
        """
        Fix an endpoint URL to ensure it uses the correct base path.
        Preserves all URL components including path and query parameters.

        Args:
            endpoint_url: The endpoint URL to fix

        Returns:
            The fixed endpoint URL
        """
        # Parse the endpoint URL
        endpoint_parsed = urlparse(endpoint_url)

        # Get the path components
        path = endpoint_parsed.path

        # If the endpoint URL is already absolute with scheme and netloc, use those
        # Otherwise use the base URL components
        scheme = endpoint_parsed.scheme or parsed_url.scheme
        netloc = endpoint_parsed.netloc or parsed_url.netloc

        # If the path doesn't start with our base path, add it
        if not path.startswith(base_path):
            # Make sure path is relative if needed
            if path.startswith("/"):
                path = path[1:]

            # Join with base path
            path = f"{base_path.rstrip('/')}/{path}"

        # Reconstruct the URL with all original components but fixed path
        # Format: scheme://netloc/path;params?query#fragment
        fixed_url = ParseResult(
            scheme=scheme,
            netloc=netloc,
            path=path,
            params=endpoint_parsed.params,
            query=endpoint_parsed.query,
            fragment=endpoint_parsed.fragment,
        ).geturl()

        logger.info(f"Fixed endpoint URL: {endpoint_url} -> {fixed_url}")
        return fixed_url

    # Create HTTP client for direct requests
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        # Create direct SSE connection
        async with aconnect_sse(
            client,
            "GET",
            url,
            timeout=httpx.Timeout(timeout, read=sse_read_timeout),
        ) as event_source:
            event_source.response.raise_for_status()
            logger.debug("SSE connection established")

            # Will store base endpoint URL received from server
            base_endpoint_url = None

            # Listen for the endpoint event from the SSE stream
            endpoint_received_event = asyncio.Event()

            async def sse_reader():
                nonlocal base_endpoint_url
                try:
                    async for sse in event_source.aiter_sse():
                        logger.debug(f"Received SSE event: {sse.event}")

                        if sse.event == "endpoint":
                            # Store the base endpoint URL (usually /message)
                            base_endpoint_url = fix_endpoint_url(sse.data)

                            # Signal that we've received the endpoint
                            endpoint_received_event.set()

                        elif sse.event == "message":
                            try:
                                # Forward the message to our read stream
                                from mcp.types import JSONRPCMessage

                                message = JSONRPCMessage.model_validate_json(sse.data)
                                logger.debug(f"Forwarding server message: {message}")
                                await read_stream_writer.send(message)
                            except Exception as exc:
                                logger.error(f"Error parsing server message: {exc}")
                                await read_stream_writer.send(exc)

                except Exception as exc:
                    logger.error(f"Error in SSE reader: {exc}")
                    await read_stream_writer.send(exc)
                finally:
                    await read_stream_writer.aclose()

            async def message_writer():
                try:
                    # Wait for the endpoint URL to be received
                    await endpoint_received_event.wait()
                    logger.info(f"Using base endpoint URL: {base_endpoint_url}")

                    async with write_stream_reader:
                        async for message in write_stream_reader:
                            logger.debug(f"Sending client message: {message}")

                            # Get endpoint from message if specified, otherwise use base endpoint
                            endpoint_url = base_endpoint_url

                            # Check if the message specifies a different endpoint
                            if hasattr(message, "endpoint") and message.endpoint:
                                # Fix the custom endpoint URL to ensure it has the base path
                                endpoint_url = fix_endpoint_url(message.endpoint)
                                logger.debug(f"Using custom endpoint from message: {endpoint_url}")

                            # Send to the fixed message endpoint URL
                            response = await client.post(
                                endpoint_url,
                                json=message.model_dump(
                                    by_alias=True,
                                    mode="json",
                                    exclude_none=True,
                                ),
                            )
                            response.raise_for_status()
                            logger.debug(f"Client message sent successfully: {response.status_code}")
                except Exception as exc:
                    logger.error(f"Error in message writer: {exc}")
                finally:
                    await write_stream.aclose()

            # Start the reader and writer tasks
            async with anyio.create_task_group() as tg:
                tg.start_soon(sse_reader)
                tg.start_soon(message_writer)

                # Yield the read and write streams
                try:
                    yield read_stream, write_stream
                finally:
                    # Cancel all tasks when done
                    tg.cancel_scope.cancel()


async def bridge_sse_to_stdio(
    url: str,
    debug: bool = False,
    timeout: float = 5.0,
    sse_read_timeout: float = 60 * 5,
    token: Optional[str] = None,
    heartbeat_interval: float = 10.0,
):
    """
    Bridge an SSE-based MCP server to stdio.

    Args:
        url: The URL of the SSE server (e.g., http://localhost:8000/sse)
        debug: Enable debug mode
        timeout: HTTP request timeout in seconds
        sse_read_timeout: SSE read timeout in seconds
        token: Authorization bearer token
        heartbeat_interval: Interval in seconds between keep-alive heartbeats
    """
    if debug:
        LoggingManager.set_level("DEBUG")
        logger.debug("Debug logging enabled")

    logger.info(f"Starting reverse bridge for SSE server: {url}")
    logger.debug(f"Bridge parameters: timeout={timeout}s, sse_read_timeout={sse_read_timeout}s")
    if token:
        logger.debug("Using authorization bearer token")

    max_retries = 5
    retry_count = 0
    retry_delay = 1.0

    while retry_count < max_retries:
        try:
            if retry_count > 0:
                logger.info(f"Reconnection attempt {retry_count}/{max_retries}")

            logger.debug("Initiating connection to SSE server")
            async with connect_sse_as_stdio(
                sse_url=url,
                timeout=timeout,
                sse_read_timeout=sse_read_timeout,
                token=token,
            ) as (_read, _write):
                # Keep the connection open until interrupted
                logger.info("Bridge established, entering keep-alive loop")
                last_heartbeat = time.time()
                retry_count = 0  # Reset retry counter on successful connection

                try:
                    while True:
                        await asyncio.sleep(heartbeat_interval)
                        current_time = time.time()
                        logger.debug(f"Keep-alive heartbeat (interval: {current_time - last_heartbeat:.2f}s)")
                        last_heartbeat = current_time

                        # Send a ping message to keep the connection alive
                        try:
                            await _write.send({"type": "ping", "timestamp": current_time})
                            logger.debug("Sent ping message to keep connection alive")
                        except Exception as e:
                            logger.warning(f"Failed to send ping: {e}")
                            raise  # Re-raise to trigger reconnection
                except (asyncio.CancelledError, KeyboardInterrupt):
                    logger.info("Bridge interrupted by user")
                    break
                except Exception as e:
                    logger.error(f"Keep-alive loop error: {e}")
                    raise  # Re-raise to trigger reconnection logic
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                logger.exception(f"Bridge connection failed after {max_retries} attempts: {e}")
                raise

            logger.warning(f"Connection error: {e}. Retrying in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 30.0)  # Exponential backoff with max of 30 seconds


def main():
    """Parse command line arguments and start the bridge."""
    parser = argparse.ArgumentParser(description="Bridge SSE-based MCP servers to stdio")
    parser.add_argument(
        "url",
        help="URL of the SSE server (e.g., http://localhost:8000/sse)",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP request timeout in seconds (default: 30.0)")
    parser.add_argument(
        "--sse-read-timeout", type=float, default=60 * 15, help="SSE read timeout in seconds (default: 900)"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--log-file", help="Log to the specified file")
    parser.add_argument("--token", help="Authorization bearer token")
    parser.add_argument("--heartbeat", type=float, default=10.0, help="Heartbeat interval in seconds (default: 10.0)")

    args = parser.parse_args()
    logger.debug(f"Command-line arguments parsed: {args}")

    # If debug mode is enabled, set logging to debug level
    if args.debug:
        LoggingManager.set_level("DEBUG")
        logger.debug("Debug logging enabled")

    # If log file is specified, enable file logging
    if args.log_file:
        LoggingManager.enable_file_logging(args.log_file)
        logger.info(f"Logging to file: {args.log_file}")

    # Run the bridge
    logger.info(f"Starting SSE-to-stdio bridge for URL: {args.url}")
    try:
        asyncio.run(
            bridge_sse_to_stdio(
                url=args.url,
                debug=args.debug,
                timeout=args.timeout,
                sse_read_timeout=args.sse_read_timeout,
                token=args.token,
                heartbeat_interval=args.heartbeat,
            )
        )
    except KeyboardInterrupt:
        logger.info("Bridge stopped by user")
    except Exception as e:
        logger.exception(f"Bridge failed: {e}")
        return 1

    logger.info("Bridge terminated successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
