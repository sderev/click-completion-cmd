"""Integration tests: end-to-end behavior, shell syntax validation, round trips."""

import shutil
import subprocess

import pytest
from click.testing import CliRunner

# -- Shell syntax validation --


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
def test_bash_script_is_valid_syntax(dummy_cli):
    """Generated bash script passes `bash -n` syntax check."""
    runner = CliRunner()
    result = runner.invoke(dummy_cli, ["completion", "bash"])
    assert result.exit_code == 0
    proc = subprocess.run(
        ["bash", "-n"],
        input=result.output,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"bash syntax error: {proc.stderr}"


@pytest.mark.skipif(shutil.which("zsh") is None, reason="zsh not available")
def test_zsh_script_is_valid_syntax(dummy_cli):
    """Generated zsh script passes `zsh -n` syntax check."""
    runner = CliRunner()
    result = runner.invoke(dummy_cli, ["completion", "zsh"])
    assert result.exit_code == 0
    proc = subprocess.run(
        ["zsh", "-n"],
        input=result.output,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"zsh syntax error: {proc.stderr}"


@pytest.mark.skipif(shutil.which("fish") is None, reason="fish not available")
def test_fish_script_is_valid_syntax(dummy_cli):
    """Generated fish script passes `fish --no-execute` syntax check."""
    runner = CliRunner()
    result = runner.invoke(dummy_cli, ["completion", "fish"])
    assert result.exit_code == 0
    proc = subprocess.run(
        ["fish", "--no-execute"],
        input=result.output,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"fish syntax error: {proc.stderr}"


# -- Install content integrity --


def test_installed_file_matches_stdout(dummy_cli, tmp_path):
    """Content written by --install matches `prog completion <shell>` stdout."""
    runner = CliRunner()
    for shell, filename in [("bash", "cli"), ("fish", "cli.fish"), ("zsh", "_cli")]:
        stdout_result = runner.invoke(dummy_cli, ["completion", shell])
        assert stdout_result.exit_code == 0

        install_dir = tmp_path / shell
        install_dir.mkdir()
        install_result = runner.invoke(
            dummy_cli, ["completion", shell, "--install", "--path", str(install_dir)]
        )
        assert install_result.exit_code == 0

        installed_content = (install_dir / filename).read_text()
        # click.echo appends one newline; strip exactly that
        assert installed_content == stdout_result.output[:-1]


# -- End-to-end round trip --


def test_install_uninstall_roundtrip(dummy_cli, tmp_path):
    """Install creates file, uninstall removes it, for each shell."""
    runner = CliRunner()
    filenames = {"bash": "cli", "fish": "cli.fish", "zsh": "_cli"}
    for shell, filename in filenames.items():
        shell_dir = tmp_path / f"roundtrip-{shell}"
        shell_dir.mkdir()

        result = runner.invoke(
            dummy_cli, ["completion", shell, "--install", "--path", str(shell_dir)]
        )
        assert result.exit_code == 0
        assert (shell_dir / filename).exists()
        assert (shell_dir / filename).read_text()  # not empty

        result = runner.invoke(
            dummy_cli, ["completion", shell, "--uninstall", "--path", str(shell_dir)]
        )
        assert result.exit_code == 0
        assert not (shell_dir / filename).exists()


# -- Prog name in installed script --


def test_installed_script_has_correct_prog_name(dummy_cli_custom_name, tmp_path):
    """Installed script for custom prog_name contains correct name and env var."""
    runner = CliRunner()
    result = runner.invoke(
        dummy_cli_custom_name, ["completion", "bash", "--install", "--path", str(tmp_path)]
    )
    assert result.exit_code == 0
    content = (tmp_path / "my-tool").read_text()
    assert "my-tool" in content
    assert "_MY_TOOL_COMPLETE" in content


# -- Completions include subcommands --


def test_completion_knows_subcommands(dummy_cli):
    """Click's completion mechanism returns the CLI's subcommands."""
    from click.shell_completion import get_completion_class
    from click_completion_cmd.shells import derive_complete_var

    cls = get_completion_class("bash")
    comp = cls(dummy_cli, {}, "cli", derive_complete_var("cli"))
    completions = comp.get_completions([], "")
    names = [c.value for c in completions]
    assert "greet" in names
    assert "completion" in names
