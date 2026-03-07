"""Add a completion subcommand to Click CLI applications."""

__version__ = "0.0.0"

from .command import make_completion_command

completion_command = make_completion_command()

__all__ = ["completion_command", "make_completion_command"]
