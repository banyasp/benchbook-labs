"""Φ grounding annotation (OPERATORS-SPEC-v1 §v1 scope; Peter 2026-11-11: observability, never a gate).

For each flip condition (would_change, would_not_change) of an extracted scenario, an LLM reads the source excerpt
around the scenario's fact spans and labels it stated | implied | authored. Results go to a sidecar file
(results/ops/phi_grounding.jsonl, one row per scenario); scenarios are not modified.

    python -m pipeline.ops grounding (--scenario ID ... | --inputs file.txt) [--window 12] [--workers 8]
"""
from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bench.schema.pipeline import Scenario
from pipeline.store import ROOT, Store

from .record import file_sha

PROMPT = Path(__file__).resolve().parent / "prompts" / "grounding.v1.md"
OUT = ROOT / "results" / "ops" / "phi_grounding.jsonl"
SPAN = re.compile(r"src:([0-9a-f]{12})#p(\d+)\.(\d+)")


def excerpt(store: Store, S: Scenario, window: int = 12, max_chars: int = 24000) -> str:
    spans = [s for v in S.fact_spans.values() for s in v]
    if not spans:
        return ""
    by_doc: dict[str, list[str]] = {}
    for s in spans:
        m = SPAN.match(s)
        if m:
            by_doc.setdefault(m.group(1), []).append(s)
    parts = []
    for sha, ss in by_doc.items():
        rows = store.doc_spans(sha)
        idx = {r["span"]: i for i, r in enumerate(rows)}
        hits = [idx[s.split("[")[0]] for s in ss if s.split("[")[0] in idx]
        if not hits:
            continue
        lo, hi = max(0, min(hits) - window), min(len(rows), max(hits) + window + 1)
        parts.append("\n".join(r["text"] for r in rows[lo:hi]))
    return "\n\n".join(parts)[:max_chars]


def ground(store: Store, sid: str, window: int = 12, role: str = "transfer_checker") -> dict:
    from pipeline.transfer.build import llm_json
    S = store.scenario(sid)
    fc = S.case.flip_conditions
    items = ([{"id": w.id, "kind": "would_change", "if": w.if_, "then": w.then} for w in fc.would_change]
             + [{"id": w.id, "kind": "would_not_change", "if": w.if_} for w in fc.would_not_change])
    src = excerpt(store, S, window)
    row = {"scenario": sid, "prompt": f"{PROMPT.name}@{file_sha(PROMPT)}", "role": role, "window": window,
           "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "n_items": len(items)}
    if not src:
        return {**row, "error": "no source spans"}
    ids = {i["id"] for i in items}
    check = lambda o: ([] if isinstance(o.get("items"), list) and {x.get("id") for x in o["items"]} == ids
                       and all(x.get("label") in ("stated", "implied", "authored") for x in o["items"])
                       else [f"label every item exactly once: {sorted(ids)}, each stated|implied|authored"])
    user = ("DECISION: " + S.case.question + "\nOPTIONS:\n" + "\n".join(f"{k}: {o.do}" for k, o in S.case.options.items())
            + f"\nVERDICT: {S.case.verdict.choice}\n\nFLIP CONDITIONS:\n" + json.dumps(items, ensure_ascii=False, indent=1)
            + "\n\nSOURCE EXCERPT:\n" + src)
    obj, log = llm_json(role, PROMPT.read_text(), user, check, tries=2)
    if obj is None:
        return {**row, "error": "no valid reply", "log": log}
    kinds = {i["id"]: i["kind"] for i in items}
    return {**row, "items": [{**x, "kind": kinds[x["id"]]} for x in obj["items"]]}


def run(store: Store, sids: list[str], window: int = 12, workers: int = 8, out: Path = OUT) -> list[dict]:
    out.parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(workers) as ex:
        rows = list(ex.map(lambda s: _safe(store, s, window), sids))
    with open(out, "a") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return rows


def _safe(store, sid, window):
    try:
        return ground(store, sid, window)
    except Exception as e:                                                # noqa: BLE001
        return {"scenario": sid, "error": f"{type(e).__name__}: {str(e)[:200]}"}
