#!/usr/bin/env bash
# pytest lives in a uv tool env without PyYAML; run it with the system python instead.
cd "$(dirname "$0")"
SP=$(ls -d /root/.local/share/uv/tools/pytest/lib/python*/site-packages 2>/dev/null | head -1)
PYTHONPATH="${SP}${PYTHONPATH:+:$PYTHONPATH}" python3 -m pytest -q "$@" tests
