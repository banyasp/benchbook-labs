"""Tiny loader for config/pipeline.yaml (flat YAML of pipeline knobs). Falls back to DEFAULTS if the file or key is missing.

    from pipeline.perturb.pconfig import get
    get("indirect_share")        # 0.7
Override the file path with env BENCHBOOK_PIPELINE_CONFIG (tests).
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

PATH = Path(__file__).resolve().parents[3] / "config" / "pipeline.yaml"
DEFAULTS = {"indirect_share": 0.7, "handup_cap": 1 / 3, "perturb_tries": 3}


def load() -> dict:
    p = Path(os.environ.get("BENCHBOOK_PIPELINE_CONFIG") or PATH)
    try:
        d = yaml.safe_load(p.read_text()) or {}
    except FileNotFoundError:
        d = {}
    return {**DEFAULTS, **d}


def get(key: str, default=None):
    return load().get(key, DEFAULTS.get(key, default))
