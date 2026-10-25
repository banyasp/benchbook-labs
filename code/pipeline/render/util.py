"""Shared helpers for the P3 operators: prompt files with version + sha12, provenance steps, tolerant JSON."""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

from bench.models import role as get_role
from bench.schema.pipeline import ProvStep, sha256_obj, sha256_text


def prompt_ref(path: Path) -> tuple[str, str, str]:
    """(text, version, sha12). Version = file stem, e.g. 'render.v1'."""
    text = Path(path).read_text()
    return text, Path(path).stem, hashlib.sha256(text.encode()).hexdigest()[:12]


def role_params(role_name: str) -> dict:
    r = get_role(role_name)
    return {"model": r.model, **{k: v for k, v in r.params.items()}}


def make_step(step_id: str, operator: str, role_name: str | None, prompt: tuple | None, inputs: dict,
              params: dict | None = None, notes: str | None = None) -> ProvStep:
    model = None
    p = dict(params or {})
    if role_name:
        r = get_role(role_name)
        model = r.model
        p = {**{k: v for k, v in r.params.items() if k in ("temperature", "max_tokens", "reasoning_effort", "samples")}, **p}
    pv = f"{prompt[1]}+{prompt[2]}" if prompt else None
    return ProvStep(id=step_id, operator=operator, model=model, role=role_name, prompt_version=pv,
                    inputs=inputs, params=p, ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), notes=notes)


def extract_json(text: str):
    """First JSON object in a model reply (tolerates fences and chatter)."""
    t = text.strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", t, re.S)
    if m:
        t = m.group(1)
    else:
        i, j = t.find("{"), t.rfind("}")
        if i < 0 or j < i:
            raise ValueError("no JSON object in reply")
        t = t[i:j + 1]
    return json.loads(t)


__all__ = ["prompt_ref", "role_params", "make_step", "extract_json", "sha256_obj", "sha256_text"]
