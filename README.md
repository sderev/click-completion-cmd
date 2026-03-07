# click-completion-cmd

Add a `completion` subcommand to your Click CLI.

Generates shell completion scripts for bash, zsh, and fish.
Installs them to the right place. Works with any Click group.

## Installation

```
pip install click-completion-cmd
```

## Quick start

```python
import click
from click_completion_cmd import completion_command

@click.group()
def cli():
    pass

cli.add_command(completion_command)
```

Your CLI now has a `completion` subcommand.

## Usage

```
prog completion bash              # print script to stdout
prog completion --install         # auto-detect shell, install
prog completion zsh --install     # explicit shell
prog completion zsh --install --path ~/.my_completions
prog completion --uninstall       # remove installed script
prog completion zsh --uninstall --path ~/.my_completions
```

When a file already exists, `--install` overwrites it and prints "Updated"
instead of "Installed."

## Shell-specific setup

### Bash

`--install` writes to `$BASH_COMPLETION_USER_DIR/completions`,
`$XDG_DATA_HOME/bash-completion/completions`, or
`~/.local/share/bash-completion/completions` (first match wins).

Modern bash-completion (>= 2.0) sources files from this directory
automatically. Alternatively, you can `eval` the output:

```bash
eval "$(prog completion bash)"
```

### Zsh

Zsh has no standard user completion directory, so `--install` prompts
for a path (default: `~/.local/share/zsh/completions`). Use `--path`
to skip the prompt. If you install with `--path DIR`, pass the same
`--path DIR` to `--uninstall` later.

After installing, add the directory printed by `--install` to your `fpath`
in `~/.zshrc`:

```zsh
fpath=(<DIR> $fpath)
autoload -Uz compinit && compinit
```

Replace `<DIR>` with the path shown in the install output.

In non-interactive contexts (CI, scripts), the prompt is skipped and the
default path is used.

### Fish

`--install` writes to `$XDG_CONFIG_HOME/fish/completions`
(default: `~/.config/fish/completions`). Fish picks up files there
automatically.

## Custom program name

When auto-detection does not return the right name (e.g., `python -m`
invocation), use `make_completion_command`:

```python
from click_completion_cmd import make_completion_command

cli.add_command(make_completion_command(prog_name="my-tool"))
```

When using a custom name, make sure your CLI launcher also passes the
same `prog_name` to Click:

```python
cli(prog_name="my-tool")
```

Otherwise the generated script targets the wrong executable.

## How it works

The library calls Click's built-in completion API to generate shell
scripts. These scripts invoke your CLI at tab-press time, so completions
update automatically whenever the CLI changes -- no manual refresh needed.

## License

Apache 2.0
