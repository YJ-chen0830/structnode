#!/usr/bin/env bash
set -euo pipefail
uv sync --all-extras --dev
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -q
