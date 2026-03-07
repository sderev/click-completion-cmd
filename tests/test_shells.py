"""Tests for the shells module."""

from pathlib import Path
from unittest.mock import patch

import click
import pytest
from click_completion_cmd.shells import (
    derive_complete_var,
    detect_shell,
    generate_completion_script,
    get_default_install_dir,
    get_install_filename,
    install_completion,
    uninstall_completion,
)

# -- detect_shell --


class TestDetectShell:
    def test_bash(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/bash")
        assert detect_shell() == "bash"

    def test_zsh(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/usr/bin/zsh")
        assert detect_shell() == "zsh"

    def test_fish(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/usr/local/bin/fish")
        assert detect_shell() == "fish"

    def test_unset_raises(self):
        # clean_shell_env already removed $SHELL
        with pytest.raises(click.ClickException, match="SHELL is not set"):
            detect_shell()

    def test_empty_raises(self, monkeypatch):
        monkeypatch.setenv("SHELL", "")
        with pytest.raises(click.ClickException, match="SHELL is not set"):
            detect_shell()

    def test_unsupported_raises(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/tcsh")
        with pytest.raises(click.ClickException, match="Unsupported shell: tcsh"):
            detect_shell()


# -- derive_complete_var --


class TestDeriveCompleteVar:
    def test_simple(self):
        assert derive_complete_var("prog") == "_PROG_COMPLETE"

    def test_hyphen(self):
        assert derive_complete_var("my-tool") == "_MY_TOOL_COMPLETE"

    def test_dot(self):
        assert derive_complete_var("my.tool") == "_MY_TOOL_COMPLETE"

    def test_hyphen_and_dot(self):
        assert derive_complete_var("my-dotted.tool") == "_MY_DOTTED_TOOL_COMPLETE"


# -- get_install_filename --


class TestGetInstallFilename:
    def test_bash(self):
        assert get_install_filename("bash", "prog") == "prog"

    def test_fish(self):
        assert get_install_filename("fish", "prog") == "prog.fish"

    def test_zsh(self):
        assert get_install_filename("zsh", "prog") == "_prog"


# -- get_default_install_dir --


class TestGetDefaultInstallDir:
    def test_default_paths_are_expanded(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        result = get_default_install_dir("zsh")
        assert result == tmp_path / ".local" / "share" / "zsh" / "completions"
        assert "~" not in str(result)

    def test_bash_default(self):
        result = get_default_install_dir("bash")
        assert result == Path.home() / ".local" / "share" / "bash-completion" / "completions"

    def test_bash_with_bash_completion_user_dir(self, monkeypatch):
        monkeypatch.setenv("BASH_COMPLETION_USER_DIR", "/custom/dir")
        assert get_default_install_dir("bash") == Path("/custom/dir/completions")

    def test_bash_colon_separated_first_entry(self, monkeypatch):
        monkeypatch.setenv("BASH_COMPLETION_USER_DIR", "/a:/b:/c")
        assert get_default_install_dir("bash") == Path("/a/completions")

    def test_bash_colon_skip_empty(self, monkeypatch):
        monkeypatch.setenv("BASH_COMPLETION_USER_DIR", ":/notempty")
        assert get_default_install_dir("bash") == Path("/notempty/completions")

    def test_bash_completion_user_dir_empty_string(self, monkeypatch):
        monkeypatch.setenv("BASH_COMPLETION_USER_DIR", "")
        result = get_default_install_dir("bash")
        assert result == Path.home() / ".local" / "share" / "bash-completion" / "completions"

    def test_bash_with_xdg_data_home(self, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", "/xdg")
        assert get_default_install_dir("bash") == Path("/xdg/bash-completion/completions")

    def test_bash_xdg_data_home_empty(self, monkeypatch):
        monkeypatch.setenv("XDG_DATA_HOME", "")
        result = get_default_install_dir("bash")
        assert result == Path.home() / ".local" / "share" / "bash-completion" / "completions"

    def test_fish_default(self):
        result = get_default_install_dir("fish")
        assert result == Path.home() / ".config" / "fish" / "completions"

    def test_fish_with_xdg_config_home(self, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", "/xdg")
        assert get_default_install_dir("fish") == Path("/xdg/fish/completions")

    def test_fish_xdg_config_home_empty(self, monkeypatch):
        monkeypatch.setenv("XDG_CONFIG_HOME", "")
        result = get_default_install_dir("fish")
        assert result == Path.home() / ".config" / "fish" / "completions"

    def test_zsh_default(self):
        result = get_default_install_dir("zsh")
        assert result == Path.home() / ".local" / "share" / "zsh" / "completions"


# -- generate_completion_script --


class TestGenerateCompletionScript:
    @pytest.fixture
    def cli_group(self):
        @click.group()
        def cli():
            pass

        @cli.command()
        def hello():
            pass

        return cli

    def test_bash_contains_complete_nosort(self, cli_group):
        script = generate_completion_script(cli_group, "prog", "bash")
        assert "complete -o nosort" in script

    def test_zsh_starts_with_compdef(self, cli_group):
        script = generate_completion_script(cli_group, "prog", "zsh")
        assert script.startswith("#compdef")

    def test_fish_contains_complete_command(self, cli_group):
        script = generate_completion_script(cli_group, "prog", "fish")
        assert "complete --no-files --command" in script

    def test_prog_name_in_script(self, cli_group):
        for shell in ("bash", "zsh", "fish"):
            script = generate_completion_script(cli_group, "prog", shell)
            assert "prog" in script

    def test_hyphenated_name_complete_var(self, cli_group):
        script = generate_completion_script(cli_group, "my-tool", "bash")
        assert "_MY_TOOL_COMPLETE" in script


# -- Bash version check side effect --


class TestBashVersionCheckSideEffect:
    @pytest.fixture
    def cli_group(self):
        @click.group()
        def cli():
            pass

        @cli.command()
        def hello():
            pass

        return cli

    def test_bash_not_on_path(self, cli_group, capsys):
        with patch("shutil.which", return_value=None):
            script = generate_completion_script(cli_group, "my-prog", "bash")
        assert "complete" in script
        assert "Couldn't detect Bash version" in capsys.readouterr().err

    def test_bash_older_than_4_4(self, cli_group, capsys):
        fake_result = type("Result", (), {"stdout": b"3.2.57(1)-release\n"})()
        with (
            patch("shutil.which", return_value="/usr/bin/bash"),
            patch("subprocess.run", return_value=fake_result),
        ):
            script = generate_completion_script(cli_group, "my-prog", "bash")
        assert "complete" in script
        assert "older than 4.4" in capsys.readouterr().err


# -- install_completion / uninstall_completion --


class TestInstallUninstall:
    @pytest.fixture
    def cli_group(self):
        @click.group()
        def cli():
            pass

        @cli.command()
        def hello():
            pass

        return cli

    def test_install_creates_file_and_parents(self, cli_group, tmp_path):
        install_dir = tmp_path / "sub" / "dir"
        path, was_update = install_completion(cli_group, "prog", "bash", install_dir)
        assert path == install_dir / "prog"
        assert path.exists()
        assert not was_update

    def test_install_fresh_returns_false(self, cli_group, tmp_path):
        _, was_update = install_completion(cli_group, "prog", "bash", tmp_path)
        assert was_update is False

    def test_install_update_returns_true(self, cli_group, tmp_path):
        install_completion(cli_group, "prog", "bash", tmp_path)
        _, was_update = install_completion(cli_group, "prog", "bash", tmp_path)
        assert was_update is True

    def test_install_content_matches_generate(self, cli_group, tmp_path):
        path, _ = install_completion(cli_group, "prog", "bash", tmp_path)
        expected = generate_completion_script(cli_group, "prog", "bash")
        assert path.read_text() == expected

    def test_install_wraps_oserror(self, cli_group, tmp_path):
        install_dir = tmp_path / "occupied"
        install_dir.write_text("x")
        with pytest.raises(click.ClickException, match="File exists"):
            install_completion(cli_group, "prog", "bash", install_dir)

    def test_install_permission_error_uses_target_path(self, cli_group, monkeypatch, tmp_path):
        install_dir = tmp_path / "completions"
        target_path = install_dir / "prog"

        def fake_write_text(self, _content):
            raise PermissionError(13, "Permission denied", str(self))

        monkeypatch.setattr(Path, "write_text", fake_write_text)
        with pytest.raises(click.ClickException) as excinfo:
            install_completion(cli_group, "prog", "bash", install_dir)
        assert str(excinfo.value) == f"Permission denied: {target_path}"

    def test_uninstall_removes_file(self, cli_group, tmp_path):
        path, _ = install_completion(cli_group, "prog", "bash", tmp_path)
        assert path.exists()
        removed_path, was_found = uninstall_completion("bash", "prog", tmp_path)
        assert removed_path == path
        assert was_found is True
        assert not path.exists()

    def test_uninstall_missing_file(self, tmp_path):
        path, was_found = uninstall_completion("bash", "prog", tmp_path)
        assert path == tmp_path / "prog"
        assert was_found is False

    def test_uninstall_wraps_oserror(self, monkeypatch, tmp_path):
        path = tmp_path / "prog"
        path.write_text("x")

        def fake_unlink(self):
            raise NotADirectoryError(20, "Not a directory", str(self))

        monkeypatch.setattr(Path, "unlink", fake_unlink)
        with pytest.raises(click.ClickException, match="Not a directory"):
            uninstall_completion("bash", "prog", tmp_path)

    def test_uninstall_permission_error_uses_target_path(self, monkeypatch, tmp_path):
        path = tmp_path / "prog"
        path.write_text("x")

        def fake_unlink(self):
            raise PermissionError(13, "Permission denied", str(self))

        monkeypatch.setattr(Path, "unlink", fake_unlink)
        with pytest.raises(click.ClickException) as excinfo:
            uninstall_completion("bash", "prog", tmp_path)
        assert str(excinfo.value) == f"Permission denied: {path}"
