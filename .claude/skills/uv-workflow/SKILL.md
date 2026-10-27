---
name: uv-workflow
description: Work with this project using uv as the package manager and build tool — syncing dependencies, running Python, tests, ruff, and pre-commit. Use this whenever running or testing code in this repo, adding a dependency, or setting up the environment, since the project pins uv to a pyenv-managed interpreter and has TLS-related version constraints that plain pip ignores.
---

# uv Development Workflow

Guidance for working with this project using `uv` as the package manager and
build tool.

## Key Commands

### Install/Sync Dependencies
```sh
uv sync
```
This installs all dependencies (including dev dependencies) as specified in `pyproject.toml`.

### Run Python Commands
```sh
uv run <command>
```
Example:
```sh
uv run pytest
uv run python main.py
uv run ruff check .
```

### Run Tests
```sh
uv run pytest
uv run pytest -v  # verbose mode
uv run pytest tests/  # specific test directory
uv run pytest --cov=lib --cov-report=term-missing  # with coverage
```

### Format Code
```sh
uv run ruff check .
uv run ruff format .
```

### Pre-commit Hooks
```sh
uv run pre-commit run --all-files
```

## Project Structure Notes

- Python 3.12 is required (pinned in `.python-version`)
- `uv` is configured to use the pyenv-managed Python (`python-preference = "only-system"`)
- Tests are located in the `tests/` directory
- Main entry points: `main.py`, `client.py`
- Library code: `lib/` directory

## TLS/Security Note

This project uses pinned versions of `certifi` and `virtualenv` to address the eMudhra/emSign CA certificate incident. Ensure any environments created outside uv maintain `pip >= 26.2.2` and `certifi >= 2026.10.19`.
