"""
Main CLI entry point for anymcp.
"""

import argparse
import sys

from anymcp import __version__
from anymcp.cli.connect_command import ConnectCommand
from anymcp.logger import LoggingManager, logger


def main():
    """Main CLI entry point."""
    logger.debug("Starting anymcp CLI")
    parser = argparse.ArgumentParser(
        "anymcp",
        usage="anymcp <command> [<args>]",
        epilog="For more information about a command, run: `anymcp <command> --help`",
        description="An adapter library for Model Context Protocol (MCP) servers.",
    )
    parser.add_argument("--version", "-v", help="Display version", action="store_true")
    parser.add_argument("--debug", help="Enable debug logging", action="store_true")
    parser.add_argument("--log-file", help="Log to the specified file")
    commands_parser = parser.add_subparsers(help="commands")

    # Register commands
    logger.debug("Registering CLI commands")
    ConnectCommand.register_subcommand(commands_parser)

    args = parser.parse_args()

    # Set debug level if requested
    if hasattr(args, "debug") and args.debug:
        LoggingManager.set_level("DEBUG")
        logger.debug("Debug logging enabled")

    # Enable file logging if specified
    if hasattr(args, "log_file") and args.log_file:
        LoggingManager.enable_file_logging(args.log_file)
        logger.info(f"Logging to file: {args.log_file}")

    if args.version:
        logger.debug(f"Displaying version: {__version__}")
        print(__version__)
        exit(0)

    if not hasattr(args, "func"):
        logger.debug("No command specified, displaying help")
        parser.print_help()
        exit(1)

    logger.info(f"Running command: {args.func.__name__}")
    command = args.func(args)
    command.run()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
        sys.exit(1)
