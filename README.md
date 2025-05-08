# AnyMCP

An adapter library for Model Context Protocol (MCP) SSE servers to connect as stdio.

## Overview

AnyMCP provides a bridge between SSE-based (Server-Sent Events) MCP servers and standard input/output (stdio). It allows you to connect to remote model servers that implement MCP over SSE and interact with them using traditional stdio interfaces.

## Features

- Connect to MCP servers via SSE endpoints
- Bridge SSE communication to standard input/output
- Maintain persistent connections with automatic reconnection
- Support for authentication via bearer tokens
- Comprehensive logging with adjustable verbosity
- Configurable timeouts and heartbeat intervals


This package is meant to be used with Arcee [AnyMCP](https://mcp.arcee.ai).
Arcee AnyMCP makes it super easy to deploy your own MCP servers.

## Installation

### Using pip

```bash
pip install anymcp
```

### From source

```bash
git clone https://github.com/arcee-ai/anymcp.git
cd anymcp
pip install -e .
```

## Usage

### Command Line Interface

Connect to an SSE-based MCP server:

```bash
anymcp connect http://localhost:8000/sse
```

With authentication:

```bash
anymcp connect http://localhost:8000/sse --token YOUR_AUTH_TOKEN
```

Add custom headers:

```bash
anymcp connect http://localhost:8000/sse --header "X-Custom-Header=Value"
```

Enable debug logging:

```bash
anymcp connect http://localhost:8000/sse --debug
```

### Python API

Use AnyMCP in your Python applications:

```python
import asyncio
from anymcp import connect_sse_as_stdio

async def main():
    async with connect_sse_as_stdio(
        sse_url="http://localhost:8000/sse",
        token="YOUR_AUTH_TOKEN",
        timeout=5.0,
        sse_read_timeout=300.0
    ) as (reader, writer):
        # Now your application can communicate with the MCP server
        # through reader and writer streams
        pass

if __name__ == "__main__":
    asyncio.run(main())
```

## Development

### Setup

```bash
# Install in development mode
pip install -e ".[dev]"
```

### Running Tests

```bash
make test
```

### Code Quality

```bash
# Format code
make style

# Check code quality
make quality
```

### Building

```bash
# Build package
make pip

# Upload to PyPI
make pip-upload
```

### Docker

```bash
# Build Docker image
make docker-buildx

# Build and push Docker image
make docker-buildx-push
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
