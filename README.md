# Roadmap

0. Smooth ASR
1. Decision layer
2. Tool calling layer
3. Memory persistence

# Installation

## Python (pyenv)

This project requires Python 3.12 (`requires-python = ">=3.12, <3.13"`). The exact
version is pinned in `.python-version`, so pyenv and uv agree on it.

```sh
brew install pyenv
pyenv install            # builds the version pinned in .python-version
pyenv global 3.12.9      # optional: default interpreter outside this repo
```

Put the shims on `PATH` in `~/.zshenv` (every shell) and initialise pyenv in
`~/.zshrc` (interactive shells):

```sh
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/shims:$PATH"
eval "$(pyenv init -)"
```

`[tool.uv]` in `pyproject.toml` pins uv to the pyenv interpreter
(`python-preference = "only-system"`, `python-downloads = "never"`), so uv never
silently downloads a second, unpinned Python.

## Install Dependencies
Install uv

Run `uv sync`

## TLS roots

`certifi` and `virtualenv` are pinned at versions carrying the fix for the
October 2026 eMudhra/emSign CA incident
(<https://discuss.python.org/t/information-for-python-users-regarding-emudhra-emsign-ca-certificate-security-incident/109576>).
Keep `pip >= 26.2.2` and `certifi >= 2026.10.19` in any environment you create
outside uv.

## Download audio model

uv run moonshine-voice download --stt --language en

Note down the model path

export MOONSHINE_MODEL_PATH=path_to_your_model