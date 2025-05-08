"""
CLI components for anymcp.
"""

from argparse import ArgumentParser

from anymcp.logger import get_logger


class BaseCLICommand:
    """Base class for CLI commands."""

    def __init__(self):
        """Initialize base command with logger."""
        self.logger = get_logger(f"anymcp.cli.{self.__class__.__name__}")

    @staticmethod
    def register_subcommand(parser: ArgumentParser):
        """
        Register a subcommand with the argument parser.

        Args:
            parser: The argument parser to register with.
        """
        raise NotImplementedError("Subclasses must implement register_subcommand")

    def run(self):
        """Execute the command."""
        raise NotImplementedError("Subclasses must implement run")


__all__ = ["BaseCLICommand"]
