"""Shared fixtures for click-completion-cmd tests."""

import click
import pytest
from click_completion_cmd import completion_command, make_completion_command


@pytest.fixture
def dummy_cli():
    """A simple Click group with a subcommand and completion_command added."""

    @click.group()
    def cli():
        pass

    @cli.command()
    @click.argument("name", default="World")
    def greet(name):
        click.echo(f"Hello, {name}!")

    cli.add_command(completion_command)
    return cli


@pytest.fixture
def dummy_cli_custom_name():
    """Same as dummy_cli but with make_completion_command(prog_name='my-tool')."""

    @click.group()
    def cli():
        pass

    @cli.command()
    @click.argument("name", default="World")
    def greet(name):
        click.echo(f"Hello, {name}!")

    cli.add_command(make_completion_command(prog_name="my-tool"))
    return cli


@pytest.fixture(autouse=True)
def clean_shell_env(monkeypatch):
    """Remove shell-related env vars so tests start from a clean state."""
    for var in (
        "SHELL",
        "BASH_COMPLETION_USER_DIR",
        "XDG_DATA_HOME",
        "XDG_CONFIG_HOME",
    ):
        monkeypatch.delenv(var, raising=False)
