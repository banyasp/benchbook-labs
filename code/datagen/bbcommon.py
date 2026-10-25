"""Shared helpers for the Benchbook datagen package: locating and importing the validator (mvp.py).

The validator is the authority on the schema. It is imported as a module from a path and never
copied or modified here. Path order: explicit argument, env BENCHBOOK_MVP, then
$BENCHBOOK_LABS/ideas/schema-mvp-2026-09-30/code/mvp.py (BENCHBOOK_LABS defaults to the repo this file
is in, then /home/claude/bb/benchbook-labs, then ~/Desktop/AI/benchbook-labs).
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MVP_RELPATH = "ideas/schema-mvp-2026-09-30/code/mvp.py"


def labs_root() -> Path:
    env = os.environ.get("BENCHBOOK_LABS")
    if env:
        return Path(env).expanduser()
    if (HERE.parents[1] / MVP_RELPATH).is_file():   # code/datagen/ inside the repo
        return HERE.parents[1]
    for cand in ("/home/claude/bb/benchbook-labs", "~/Desktop/AI/benchbook-labs"):
        if Path(cand).expanduser().is_dir():
            return Path(cand).expanduser()
    return Path("/home/claude/bb/benchbook-labs")


def mvp_path(explicit: str | None = None) -> Path:
    p = explicit or os.environ.get("BENCHBOOK_MVP") or str(labs_root() / MVP_RELPATH)
    return Path(p).expanduser()


def load_mvp(explicit: str | None = None):
    """Import mvp.py from its path (never copied). Raises FileNotFoundError with a usable message."""
    path = mvp_path(explicit)
    if not path.is_file():
        raise FileNotFoundError(f"validator not found at {path}; pass --mvp PATH or set BENCHBOOK_MVP")
    spec = importlib.util.spec_from_file_location("benchbook_mvp", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["benchbook_mvp"] = mod
    spec.loader.exec_module(mod)
    mod.__benchbook_path__ = str(path)
    return mod


def examples_dir() -> Path:
    return labs_root() / "examples-v21"


def words(text) -> int:
    return len(str(text).split())
