"""Shell detection, path resolution, and completion script generation."""

from __future__ import annotations

import os
from pathlib import Path

import click
from click.shell_completion import get_completion_class

SUPPORTED_SHELLS = ("bash", "zsh", "fish")


def detect_shell() -> str:
    """Detect shell from $SHELL. Raise click.ClickException on failure."""
    shell_env = os.environ.get("SHELL", "")
    if not shell_env:
        raise click.ClickException(
            "Cannot detect shell: $SHELL is not set. Specify the shell explicitly."
        )
    name = Path(shell_env).name
    if name not in SUPPORTED_SHELLS:
        raise click.ClickException(
            f"Unsupported shell: {name}. Supported shells: {', '.join(SUPPORTED_SHELLS)}"
        )
    return name


def derive_complete_var(prog_name: str) -> str:
    """Derive _PROG_COMPLETE env var name from prog_name."""
    name = prog_name.upper().replace("-", "_").replace(".", "_")
    return f"_{name}_COMPLETE"


def get_default_install_dir(shell: str) -> Path:
    """Resolve default install directory per shell, respecting XDG/env vars.

    Treat empty env vars as unset per XDG spec.
    Colon-split $BASH_COMPLETION_USER_DIR, use first non-empty entry.
    All paths through Path.expanduser().
    """
    match shell:
        case "bash":
            bash_comp_dir = os.environ.get("BASH_COMPLETION_USER_DIR", "")
            if bash_comp_dir:
                for entry in bash_comp_dir.split(":"):
                    entry = entry.strip()
                    if entry:
                        return Path(entry).expanduser() / "completions"
            xdg_data = os.environ.get("XDG_DATA_HOME", "")
            if xdg_data:
                return Path(xdg_data).expanduser() / "bash-completion" / "completions"
            return Path("~/.local/share/bash-completion/completions").expanduser()
        case "fish":
            xdg_config = os.environ.get("XDG_CONFIG_HOME", "")
            if xdg_config:
                return Path(xdg_config).expanduser() / "fish" / "completions"
            return Path("~/.config/fish/completions").expanduser()
        case "zsh":
            return Path("~/.local/share/zsh/completions").expanduser()
        case _:
            raise click.ClickException(f"Unsupported shell: {shell}")


def get_install_filename(shell: str, prog_name: str) -> str:
    """Return filename: {prog} for bash, {prog}.fish for fish, _{prog} for zsh."""
    match shell:
        case "bash":
            return prog_name
        case "fish":
            return f"{prog_name}.fish"
        case "zsh":
            return f"_{prog_name}"
        case _:
            raise click.ClickException(f"Unsupported shell: {shell}")


def generate_completion_script(cli: click.BaseCommand, prog_name: str, shell: str) -> str:
    """Generate completion script using Click's API."""
    cls = get_completion_class(shell)
    if cls is None:
        raise click.ClickException(f"Unsupported shell: {shell}")
    complete_var = derive_complete_var(prog_name)
    comp = cls(cli, {}, prog_name, complete_var)
    return comp.source()


def install_completion(
    cli: click.BaseCommand, prog_name: str, shell: str, install_dir: Path
) -> tuple[Path, bool]:
    """Write completion script to install_dir/filename.

    Create parent dirs. Return (path, was_update).
    Raise click.ClickException on filesystem errors.
    """
    filename = get_install_filename(shell, prog_name)
    path = install_dir / filename
    was_update = path.exists()
    script = generate_completion_script(cli, prog_name, shell)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(script)
    except OSError as exc:
        raise _wrap_filesystem_error(path, exc) from exc
    return path, was_update


def uninstall_completion(shell: str, prog_name: str, install_dir: Path) -> tuple[Path, bool]:
    """Remove completion file. Return (path, was_found).

    Raise click.ClickException on filesystem errors.
    """
    filename = get_install_filename(shell, prog_name)
    path = install_dir / filename
    was_found = path.exists()
    if was_found:
        try:
            path.unlink()
        except OSError as exc:
            raise _wrap_filesystem_error(path, exc) from exc
    return path, was_found


def _wrap_filesystem_error(path: Path, exc: OSError) -> click.ClickException:
    """Format filesystem errors for CLI display."""
    if isinstance(exc, PermissionError):
        return click.ClickException(f"Permission denied: {path}")
    return click.ClickException(str(exc))
