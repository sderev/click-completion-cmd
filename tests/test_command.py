"""Tests for the completion Click command via CliRunner."""

from types import SimpleNamespace
from unittest.mock import patch

import click
from click.testing import CliRunner
from click_completion_cmd import completion_command

# -- Stdout output --


class TestStdoutOutput:
    def test_bash_output(self, dummy_cli):
        result = CliRunner().invoke(dummy_cli, ["completion", "bash"])
        assert result.exit_code == 0
        assert "complete -o nosort" in result.output

    def test_zsh_output(self, dummy_cli):
        result = CliRunner().invoke(dummy_cli, ["completion", "zsh"])
        assert result.exit_code == 0
        assert result.output.startswith("#compdef")

    def test_fish_output(self, dummy_cli):
        result = CliRunner().invoke(dummy_cli, ["completion", "fish"])
        assert result.exit_code == 0
        assert "complete --no-files --command" in result.output


# -- Install --


class TestInstall:
    def test_bash_install(self, dummy_cli, tmp_path):
        result = CliRunner().invoke(
            dummy_cli, ["completion", "bash", "--install", "--path", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert (tmp_path / "cli").exists()
        assert "Installed" in result.output

    def test_bash_install_update(self, dummy_cli, tmp_path):
        CliRunner().invoke(dummy_cli, ["completion", "bash", "--install", "--path", str(tmp_path)])
        result = CliRunner().invoke(
            dummy_cli, ["completion", "bash", "--install", "--path", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "Updated" in result.output

    def test_fish_install_filename(self, dummy_cli, tmp_path):
        result = CliRunner().invoke(
            dummy_cli, ["completion", "fish", "--install", "--path", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert (tmp_path / "cli.fish").exists()

    def test_zsh_install_filename(self, dummy_cli, tmp_path):
        result = CliRunner().invoke(
            dummy_cli, ["completion", "zsh", "--install", "--path", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert (tmp_path / "_cli").exists()

    def test_install_auto_detects_bash_from_shell_env(self, dummy_cli, tmp_path, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/bash")
        result = CliRunner().invoke(dummy_cli, ["completion", "--install", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert (tmp_path / "cli").exists()
        assert "bash completion" in result.output

    def test_path_flag_expands_tilde(self, dummy_cli, tmp_path):
        home_dir = tmp_path / "home"
        home_dir.mkdir()
        result = CliRunner().invoke(
            dummy_cli,
            ["completion", "bash", "--install", "--path", "~/custom"],
            env={"HOME": str(home_dir)},
        )
        assert result.exit_code == 0
        assert (home_dir / "custom" / "cli").exists()


# -- Uninstall --


class TestUninstall:
    def test_uninstall_removes_file(self, dummy_cli, tmp_path):
        CliRunner().invoke(dummy_cli, ["completion", "bash", "--install", "--path", str(tmp_path)])
        result = CliRunner().invoke(
            dummy_cli, ["completion", "bash", "--uninstall", "--path", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "Removed" in result.output
        assert not (tmp_path / "cli").exists()

    def test_uninstall_missing_file(self, dummy_cli, tmp_path):
        result = CliRunner().invoke(
            dummy_cli, ["completion", "bash", "--uninstall", "--path", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "No completion file found" in result.output

    def test_uninstall_auto_detects_zsh_from_shell_env(self, dummy_cli, tmp_path, monkeypatch):
        CliRunner().invoke(dummy_cli, ["completion", "zsh", "--install", "--path", str(tmp_path)])
        monkeypatch.setenv("SHELL", "/usr/bin/zsh")
        result = CliRunner().invoke(
            dummy_cli, ["completion", "--uninstall", "--path", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "Removed zsh completion" in result.output
        assert not (tmp_path / "_cli").exists()


# -- Zsh interactive prompt --


class TestZshPrompt:
    def test_zsh_install_custom_path_via_prompt(self, dummy_cli, tmp_path):
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()
        with (
            patch(
                "click_completion_cmd.command.sys",
                SimpleNamespace(stdin=SimpleNamespace(isatty=lambda: True)),
            ),
            patch("click_completion_cmd.command.input", return_value=str(custom_dir)),
        ):
            result = CliRunner().invoke(dummy_cli, ["completion", "zsh", "--install"])
        assert result.exit_code == 0
        assert (custom_dir / "_cli").exists()

    def test_zsh_install_default_via_prompt(self, dummy_cli, tmp_path, monkeypatch):
        default_dir = tmp_path / "zsh" / "completions"
        monkeypatch.setattr(
            "click_completion_cmd.command.get_default_install_dir", lambda _: default_dir
        )
        with (
            patch(
                "click_completion_cmd.command.sys",
                SimpleNamespace(stdin=SimpleNamespace(isatty=lambda: True)),
            ),
            patch("click_completion_cmd.command.input", return_value="") as mock_input,
        ):
            result = CliRunner().invoke(dummy_cli, ["completion", "zsh", "--install"])
        mock_input.assert_called_once()
        assert result.exit_code == 0
        assert (default_dir / "_cli").exists()
        assert "zsh completion for cli" in result.output
        assert str(default_dir / "_cli") in result.output

    def test_zsh_install_path_flag_skips_prompt(self, dummy_cli, tmp_path):
        with patch("click_completion_cmd.command.input") as mock_input:
            result = CliRunner().invoke(
                dummy_cli,
                ["completion", "zsh", "--install", "--path", str(tmp_path)],
            )
        mock_input.assert_not_called()
        assert result.exit_code == 0
        assert (tmp_path / "_cli").exists()

    def test_zsh_install_eof_uses_default(self, dummy_cli, tmp_path, monkeypatch):
        default_dir = tmp_path / "zsh" / "completions"
        monkeypatch.setattr(
            "click_completion_cmd.command.get_default_install_dir", lambda _: default_dir
        )
        with (
            patch(
                "click_completion_cmd.command.sys",
                SimpleNamespace(stdin=SimpleNamespace(isatty=lambda: True)),
            ),
            patch("click_completion_cmd.command.input", side_effect=EOFError),
        ):
            result = CliRunner().invoke(dummy_cli, ["completion", "zsh", "--install"])
        assert result.exit_code == 0
        assert (default_dir / "_cli").exists()
        assert "zsh completion for cli" in result.output
        assert str(default_dir / "_cli") in result.output

    def test_zsh_prompt_shows_tilde_not_absolute_home(self, dummy_cli, tmp_path, monkeypatch):
        default_dir = tmp_path / "zsh" / "completions"
        monkeypatch.setattr(
            "click_completion_cmd.command.get_default_install_dir", lambda _: default_dir
        )
        monkeypatch.setattr(
            "click_completion_cmd.command.Path.home", staticmethod(lambda: tmp_path)
        )
        with (
            patch(
                "click_completion_cmd.command.sys",
                SimpleNamespace(stdin=SimpleNamespace(isatty=lambda: True)),
            ),
            patch("click_completion_cmd.command.input", return_value="") as mock_input,
        ):
            result = CliRunner().invoke(dummy_cli, ["completion", "zsh", "--install"])
        prompt_text = mock_input.call_args[0][0]
        assert "~/zsh/completions" in prompt_text
        assert str(tmp_path) not in prompt_text
        assert result.exit_code == 0

    def test_zsh_install_non_interactive_uses_default_without_prompt(
        self, dummy_cli, tmp_path, monkeypatch
    ):
        default_dir = tmp_path / "zsh" / "completions"
        monkeypatch.setattr(
            "click_completion_cmd.command.get_default_install_dir", lambda _: default_dir
        )
        with patch(
            "click_completion_cmd.command.sys",
            SimpleNamespace(stdin=SimpleNamespace(isatty=lambda: False)),
        ):
            result = CliRunner().invoke(dummy_cli, ["completion", "zsh", "--install"])
        assert result.exit_code == 0
        assert (default_dir / "_cli").exists()
        assert "Enter path" not in result.output


# -- Error cases --


class TestErrorCases:
    def test_no_shell_no_flags(self, dummy_cli):
        result = CliRunner().invoke(dummy_cli, ["completion"])
        assert result.exit_code != 0
        assert "Shell argument required" in result.output

    def test_install_and_uninstall(self, dummy_cli):
        result = CliRunner().invoke(dummy_cli, ["completion", "bash", "--install", "--uninstall"])
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output

    def test_path_without_action(self, dummy_cli):
        result = CliRunner().invoke(dummy_cli, ["completion", "bash", "--path", "/foo"])
        assert result.exit_code != 0
        assert "--path requires" in result.output

    def test_path_rejects_file(self, dummy_cli, tmp_path):
        file_path = tmp_path / "not-a-directory"
        file_path.write_text("x")
        result = CliRunner().invoke(
            dummy_cli,
            ["completion", "bash", "--install", "--path", str(file_path)],
        )
        assert result.exit_code != 0
        assert "is a file" in result.output

    def test_invalid_shell(self, dummy_cli):
        result = CliRunner().invoke(dummy_cli, ["completion", "tcsh"])
        assert result.exit_code != 0
        assert "tcsh" in result.output


# -- Prog name override --


class TestProgNameOverride:
    def test_custom_prog_name_in_script(self, dummy_cli_custom_name):
        result = CliRunner().invoke(dummy_cli_custom_name, ["completion", "bash"])
        assert result.exit_code == 0
        assert "my-tool" in result.output
        assert "_MY_TOOL_COMPLETE" in result.output


# -- Shared singleton --


class TestSharedSingleton:
    def test_same_command_different_groups(self):
        @click.group()
        def group_a():
            pass

        @click.group()
        def group_b():
            pass

        group_a.add_command(completion_command)
        group_b.add_command(completion_command)

        runner = CliRunner()

        result_a = runner.invoke(group_a, ["completion", "bash"], prog_name="tool-a")
        assert result_a.exit_code == 0
        assert "tool-a" in result_a.output

        result_b = runner.invoke(group_b, ["completion", "bash"], prog_name="tool-b")
        assert result_b.exit_code == 0
        assert "tool-b" in result_b.output
