# python-automation-starter

Production-ready Python automation boilerplate — argparse CLI, structured logging, `.env` config, Makefile, and Docker support.

Stop copying `if __name__ == "__main__":` boilerplate from your last script. Clone this, rename one folder, and ship.

## What's in the box

| File | Purpose |
|------|---------|
| `main.py` | Entrypoint with argparse subcommands and `--log-level` plumbing |
| `env_loader.py` | Load and type-coerce `.env` values, with required-key validation |
| `retry.py` | Decorator for exponential-backoff retries with jitter and max attempts |
| `pyproject.toml` | PEP 621 metadata, ruff + mypy config, `pytest` discovery rules |
| `tests/` | Smoke tests for each module — patterns to copy when you add new ones |
| `examples/upi_reconcile.py` | Reconciles PhonePe/GPay/Paytm CSV exports into one Excel file with monthly category totals |

## Getting Started

```bash
# 1. Use this repo as a template
git clone https://github.com/archit-akg13/python-automation-starter.git my-new-script
cd my-new-script
rm -rf .git && git init

# 2. Set up a virtualenv
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 3. Create your .env from the template
cp .env.example .env  # then edit values

# 4. Run it
python -m main hello --name "Archit"
python -m main --log-level DEBUG batch --input data.csv
```

## Why these defaults

Every choice in this starter exists because a previous script broke without it:

- **`argparse` over `click` / `typer`** — zero dependencies, works on any Python ≥ 3.10, copy-pasteable into restricted environments.
- **Structured logging to stderr in JSON** — output stays parseable for log shippers; humans get a `--log-format text` flag.
- **`.env` for config, not flags** — secrets and per-environment values stay out of shell history and CI logs.
- **Retry decorator with explicit policy** — every external call must declare its retry budget; "3 retries, 200ms base, 2x backoff, 30s ceiling" is the default but is overridable per-call.
- **Tests that run in under a second** — the smoke suite is meant to gate every commit. Slow integration tests live in `tests/integration/` and are excluded by default.

## Adding a new subcommand

Three steps — the structure is intentionally repetitive so you can pattern-match:

1. Add a new file `commands/<name>.py` with a `register(subparsers)` function and a `run(args)` function.
2. Import and call `register` from `main.py`.
3. Add `tests/test_<name>.py` with at least one happy-path test.

That's it. No plugin system, no service container, no metaclass magic. The dispatch is a dict in `main.py` you can read top to bottom.

## Make targets

```make
make install   # pip install -e ".[dev]"
make test      # pytest -q
make lint      # ruff check . && mypy .
make fmt       # ruff format .
make run ARGS="hello --name World"
make docker    # build the image
```

## License

MIT — fork it, rename it, ship it.
# python-automation-starter
Production-ready Python automation boilerplate — argparse CLI, structured logging, .env config, Makefile, and Docker support.

## Project layout

The template is intentionally small. Everything you might want to delete on a real project lives in `examples/` or `tests/`, so the root stays scannable.

```
python-automation-starter/
  main.py            # argparse entrypoint with subcommands
  env_loader.py      # .env parsing with type coercion
  retry.py           # backoff decorator with jitter
  pyproject.toml     # ruff, mypy, pytest config
  examples/          # delete or replace these
  tests/             # smoke tests for retry and env_loader
```

## Why subcommands instead of separate scripts

A single `main.py` with subcommands gives you one place to put shared concerns: logging setup, the global `--log-level` flag, signal handlers for clean shutdown. Each subcommand stays small because the boring plumbing only exists once. When you copy this repo to start a new tool, you keep that single entrypoint and add a new subcommand under `main.py` rather than duplicating boilerplate across N scripts.

## Development workflow

The `Makefile` exposes the four commands you actually run during development:

  make install   installs the project in editable mode with dev extras
    make lint      runs ruff check and mypy in one pass
      make test      runs pytest with coverage and fails if coverage drops below 80 percent
        make run       runs main.py with sensible defaults for local exploration

        If you don't have make installed, the README of each subcommand shows the equivalent raw commands.
        
