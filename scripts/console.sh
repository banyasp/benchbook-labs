#!/usr/bin/env bash
# Start the Benchbook research console on 127.0.0.1:${PORT:-8765} (local only; forward the port over SSH to view it).
cd "$(dirname "$0")/.."
export PYTHONPATH=code
exec .venv/bin/python -m console --port "${PORT:-8765}"
