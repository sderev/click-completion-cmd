"""Click command implementation for shell completion management."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from .shells import (
    detect_shell,
    generate_completion_script,
    get_default_install_dir,
    install_completion,
    uninstall_completion,
)


def make_completion_command(prog_name: str | None = None) -> click.Command:
    """Factory that creates the completion Click command."""

    @click.command("completion")
    @click.argument(
        "shell",
        required=False,
        type=click.Choice(["bash", "zsh", "fish"]),
    )
    @click.option("--install", "do_install", is_flag=True, help="Install completion.")
    @click.option("--uninstall", "do_uninstall", is_flag=True, help="Uninstall completion.")
    @click.option(
        "--path",
        "custom_path",
        type=click.Path(file_okay=False, path_type=Path),
        default=None,
        help="Custom directory for install/uninstall.",
    )
    @click.pass_context
    def completion(
        ctx: click.Context,
        shell: str | None,
        do_install: bool,
        do_uninstall: bool,
        custom_path: Path | None,
    ) -> None:
        """Generate or install shell completion scripts."""
        # Validate flag combinations first (before any shell detection)
        if do_install and do_uninstall:
            raise click.ClickException("--install and --uninstall are mutually exclusive.")

        if custom_path and not do_install and not do_uninstall:
            raise click.ClickException("--path requires --install or --uninstall.")

        # Validate: bare command (no shell, no flags) -> error
        if shell is None and not do_install and not do_uninstall:
            raise click.ClickException("Shell argument required. Use: completion <bash|zsh|fish>")

        # Resolve prog_name
        resolved_prog = prog_name or ctx.find_root().info_name

        # Resolve shell (auto-detect if not given and an action flag is set)
        if shell is None and (do_install or do_uninstall):
            shell = detect_shell()

        # Get root CLI object for script generation
        root_cli = ctx.find_root().command

        if do_install:
            install_dir = _resolve_install_dir(shell, custom_path)
            path, was_update = install_completion(root_cli, resolved_prog, shell, install_dir)
            action = "Updated" if was_update else "Installed"
            click.echo(f"{action} {shell} completion for {resolved_prog} to {path}")
            if shell == "zsh":
                click.echo(
                    f"\nIf not already in your ~/.zshrc, add:\n"
                    f"  fpath=({install_dir} $fpath)\n"
                    f"  autoload -Uz compinit && compinit"
                )
        elif do_uninstall:
            install_dir = _resolve_uninstall_dir(shell, custom_path)
            path, was_found = uninstall_completion(shell, resolved_prog, install_dir)
            if was_found:
                click.echo(f"Removed {shell} completion for {resolved_prog} from {path}")
            else:
                click.echo(f"No completion file found at {path}")
        else:
            # Shell given, no flags -> output script to stdout
            script = generate_completion_script(root_cli, resolved_prog, shell)
            click.echo(script)

    return completion


def _compact_home(path: Path) -> str:
    """Replace the home directory prefix with ``~`` for display."""
    try:
        return "~/" + str(path.relative_to(Path.home()))
    except ValueError:
        return str(path)


def _resolve_install_dir(shell: str, custom_path: Path | None) -> Path:
    """Resolve install directory, prompting for zsh if needed."""
    if custom_path:
        return custom_path.expanduser()

    if shell == "zsh":
        default_dir = get_default_install_dir("zsh")
        if not sys.stdin.isatty():
            return default_dir
        display = _compact_home(default_dir)
        try:
            user_input = input(
                f"Zsh has no standard completion directory.\nEnter path [{display}]: "
            )
        except EOFError:
            return default_dir
        user_input = user_input.strip()
        if user_input:
            return Path(user_input).expanduser()
        return default_dir

    return get_default_install_dir(shell)


def _resolve_uninstall_dir(shell: str, custom_path: Path | None) -> Path:
    """Resolve uninstall directory."""
    if custom_path:
        return custom_path.expanduser()
    return get_default_install_dir(shell)
