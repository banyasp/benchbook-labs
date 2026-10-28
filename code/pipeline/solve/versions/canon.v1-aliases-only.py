"""Canonicalize a sampled reply before the RS filter (batch 2026-10-28).

In the first live run 0/24 Granite samples passed the strict parse, mostly for format slips that carry no reasoning:
an off-enum value (`kind: policy`, `weight: moderate`), an omitted empty bucket (`corresponding:`), an extra key the
schema forbids. `canonicalize` repairs exactly those, driven by the schema's own validation errors, re-serializes the
steps in the PDF order (mode C layout: structure inside <think>, the verdict outside), and re-parses. The SFT target is
the canonical text (`target_text`), so training never teaches an off-enum value. Every fix is returned and logged.
What it never touches: ids, mappings' content, choices, relations, `via`, prose.
"""
from __future__ import annotations

import copy

import yaml
from pydantic import ValidationError

from bench.schema.reply import MODELS, STEPS, parse_reply

ALIASES = {
    "kind": {"policy": "authority", "rule": "authority", "regulation": "authority", "law": "authority",
             "constraint": "authority", "permission": "authority", "assessment": "intelligence", "analysis": "intelligence",
             "evidence": "intelligence", "fact": "situation", "context": "situation", "event": "situation",
             "background": "situation", "resource": "capability", "tool": "capability", "ability": "capability"},
    "weight": {"moderate": "weak", "medium": "weak", "low": "weak", "minor": "weak", "high": "strong", "major": "strong",
               "decisive": "strong", "critical": "strong"},
    "status": {"assumed": "assessed", "probable": "assessed", "likely": "assessed", "reported": "assessed",
               "unconfirmed": "assessed", "verified": "confirmed", "known": "confirmed"},
}
LIST_FIELDS = {"matched", "corresponding", "live_only", "case_only"}
MAX_PASSES = 8


def _get(d, loc):
    for k in loc[:-1]:
        d = d[k]
    return d


def fix_step(kind: str, data: dict) -> tuple[dict, list[str]]:
    d, fixes = copy.deepcopy(data), []
    for _ in range(MAX_PASSES):
        try:
            MODELS[kind].model_validate(d)
            return d, fixes
        except ValidationError as e:
            changed = False
            for err in e.errors():
                loc, typ = err["loc"], err["type"]
                try:
                    parent, key = _get(d, loc), loc[-1]
                except (KeyError, IndexError, TypeError):
                    continue
                if typ == "extra_forbidden" and isinstance(parent, dict) and key in parent:
                    parent.pop(key)
                    fixes.append(f"{kind}.{'.'.join(map(str, loc))}: dropped extra key")
                    changed = True
                elif typ == "missing" and key in LIST_FIELDS and isinstance(parent, dict):
                    parent[key] = []
                    fixes.append(f"{kind}.{key}: filled empty list")
                    changed = True
                elif typ == "literal_error" and isinstance(parent, dict) and isinstance(parent.get(key), str):
                    v = parent[key].strip().lower()
                    alias = ALIASES.get(str(key), {}).get(v)
                    if alias:
                        parent[key] = alias
                        fixes.append(f"{kind}.{'.'.join(map(str, loc))}: {v} -> {alias}")
                        changed = True
            if not changed:
                return d, fixes
    return d, fixes


def _dump(kind: str, d: dict) -> str:
    body = {k: v for k, v in d.items() if k != "kind"}
    return yaml.safe_dump({"kind": kind, **body}, sort_keys=False, allow_unicode=True, width=120).strip()


def canonicalize(raw_text: str, *, noref: bool = False) -> tuple[str | None, list[str]]:
    """-> (canonical mode-C text, fixes) when the repaired reply parses strictly; (None, fixes) otherwise.
    A reply that already parses strictly is returned re-serialized with no fixes."""
    p = parse_reply(raw_text, noref=noref)
    steps = [k for k in STEPS if k in p.steps]
    if p.missing:
        return None, [f"missing {p.missing}"]
    fixes, docs = [], []
    for k in steps:
        d, f = fix_step(k, p.steps[k])
        fixes += f
        docs.append(_dump(k, d))
    fixes += [f"parser repair: {r}" for rs in p.repairs.values() for r in rs]
    text = "<think>\n" + "\n---\n".join(docs[:-1]) + "\n</think>\n" + docs[-1] + "\n"
    q = parse_reply(text, noref=noref)
    return (text if q.strict_ok else None), fixes
