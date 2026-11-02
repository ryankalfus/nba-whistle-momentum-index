#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python_command="${PYTHON:-python3.14}"
"$python_command" -c 'import sys; assert sys.version_info[:3] == (3, 14, 7), "Use Python 3.14.7 (see .python-version)"'
"$python_command" -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
.venv/bin/python -m pip install --no-build-isolation --no-deps -e .
.venv/bin/python -m whistle_research environment
