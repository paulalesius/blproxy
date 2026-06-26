#!/bin/bash
set -e

cd "$(dirname "$0")"

# Run tests using the existing .venv
.venv/bin/python -m pytest tests/ -v --timeout=60
