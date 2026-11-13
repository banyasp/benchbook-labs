"""Console data for SFT target-generation runs (2026-11-13, Peter: make the SFT prompts visible in the console).

A run directory is `results/sft/<run>/` with cells.json and the stage outputs of `pipeline.sft.wexp` (write.jsonl,
granite.jsonl, guided*.jsonl). The cell page REBUILDS every prompt with the current code (pipeline.sft.targets), so it
shows exactly what generation sends now; the prompt files themselves are listed on /prompts with their versions.
"""
from __future__ import annotations

import json
import statistics as st
from functools import lru_cache
from pathlib import Path

from bench.models import ROOT

SFT = ROOT / "results" / "sft"
PROMPT_DIR = "code/pipeline/sft/prompts"
STAGES = [("write.jsonl", "Luna writes the full target (writer.v1.md)"),
          ("granite.jsonl", "Granite restate (retired) · Granite alone after gold prefill (k=8) · random arm no-case W+V"),
          ("guided.jsonl", "Granite with Luna's notes (notes.v1.md), k=2"),
          ("guided-ca.jsonl", "Granite with Luna's notes + case_approach guidance (case_approach_guide.v1.md), k=2 — CHOSEN"),
          ("wv.jsonl", "Production run (pipeline.sft.generate): the chosen W+V step with gates, Luna fallback; random arm "
                       "no-case W+V"),
          ("sft.jsonl", "Assembled SFT rows (prompt = mode-B generation prompt, completion = target)")]


def _wv(r: Path) -> dict:
    """A production run's wv.jsonl, in the shapes the experiment pages use (guided rounds flattened; random samples
    as `nocase`)."""
    out = {}
    for x in _jl(r / "wv.jsonl"):
        x["guided"] = [s for rd in x.get("rounds") or [] for s in rd]
        x["nocase"] = x.get("samples") or []
        out[x["cell"]] = x
    return out


def _jl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def runs() -> list[dict]:
    out = []
    for d in sorted(SFT.glob("*/cells.json")):
        r = d.parent
        out.append({"run": str(r.relative_to(ROOT)), "name": r.name, "cells": len(json.loads(d.read_text())),
                    "stages": [f for f, _ in STAGES if (r / f).exists()],
                    "config": json.loads((r / "config.json").read_text()) if (r / "config.json").exists() else {}})
    return out


def _acc(ss):
    return sum(bool(s.get("accepted")) for s in ss or []), len(ss or [])


def run_overview(run: str) -> dict:
    r = ROOT / run
    cells = json.loads((r / "cells.json").read_text())
    W = {x["cell"]: x for x in _jl(r / "write.jsonl")}
    G = {x["cell"]: x for x in _jl(r / "granite.jsonl")}
    GU = {x["cell"]: x for x in _jl(r / "guided.jsonl")}
    GC = {x["cell"]: x for x in _jl(r / "guided-ca.jsonl")}
    V = _wv(r)
    for cid, x in V.items():
        GC.setdefault(cid, x)
        G.setdefault(cid, x)
    rows = []
    for c in cells:
        cid = c["cell"]
        w, g, gu, gc = W.get(cid, {}), G.get(cid, {}), GU.get(cid, {}), GC.get(cid, {})
        cas = [s["ca"]["p_case_account"] for s in gc.get("guided") or [] if s.get("ca")]
        rows.append({"cell": cid, "arm": c["arm"], "x1": c["x1"], "x2": c["x2"], "relation": w.get("relation"),
                     "luna": w.get("accepted"), "rs": _acc(g.get("granite_rs")), "guided": _acc(gu.get("guided")),
                     "guided_ca": _acc(gc.get("guided")), "nocase": len([s for s in g.get("nocase") or [] if s.get("text")]),
                     "ca_p": round(st.median(cas), 2) if cas else None,
                     "source": (V.get(cid) or {}).get("source", "") if cid in V else None})
    prompts = sorted(p.name for p in (ROOT / PROMPT_DIR).glob("*") if p.is_file())
    report = (r / "report.md").read_text() if (r / "report.md").exists() else ""
    return {"run": run, "rows": rows, "stages": [(f, d, (r / f).exists()) for f, d in STAGES], "prompts": prompts,
            "prompt_dir": PROMPT_DIR, "report": report,
            "config": json.loads((r / "config.json").read_text()) if (r / "config.json").exists() else {}}


@lru_cache(maxsize=1)
def _store():
    from pipeline.store import Store
    return Store()


def _msgs_text(msgs: list[dict]) -> str:
    return "\n\n".join(f"===== [{m['role']}] =====\n{m['content']}" for m in msgs)


def cell_detail(run: str, cell: str) -> dict:
    from pipeline.sft import targets as T
    r = ROOT / run
    c = next(x for x in json.loads((r / "cells.json").read_text()) if x["cell"] == cell)
    w = next((x for x in _jl(r / "write.jsonl") if x["cell"] == cell), {})
    g = next((x for x in _jl(r / "granite.jsonl") if x["cell"] == cell), {})
    gu = next((x for x in _jl(r / "guided.jsonl") if x["cell"] == cell), {})
    gc = next((x for x in _jl(r / "guided-ca.jsonl") if x["cell"] == cell), {})
    v = _wv(r).get(cell)
    if v:
        gc, g = gc or v, g or v
    out = {"cell": c, "write": w, "granite": g, "guided": gu.get("guided") or [], "guided_ca": gc.get("guided") or [],
           "prompts": {}, "error": None, "final": v}
    try:
        p = T.prepare(_store(), c, aligned=w.get("aligner"))
        out["gold"] = {"relation": p.g.pair.relation, "choice": p.g.choice, "via": p.g.via, "governs": p.g.pair.governs,
                       "strategy": p.built.strategy, "warnings": p.g.warnings, "notes": p.built.notes}
        out["prompts"]["training"] = {"what": "SFT training prompt = the plain student prompt (format.v3, mode B). The "
                                              "target follows it as the assistant reply; no notes, no guidance.",
                                      "text": _msgs_text(p.ep.messages)}
        out["prompts"]["writer"] = {"what": "Luna writer (role sft_writer): system = writer.v1.md; user = student prompt "
                                            "+ gold structure + fixed F/K documents.",
                                    "text": _msgs_text(T.writer_messages(p))}
        if w.get("text") and p.g.pair.relation != "not_governed":
            ep, prefill = T.guided_episode(p, w["text"], guide=True)
            base = p.ep.messages[-1]["content"]
            added = ep.messages[-1]["content"][len(base):]
            out["prompts"]["granite"] = {
                "what": "Granite with notes + case_approach guidance (the chosen pipeline): the student prompt, with this "
                        "text appended to its last user message (notes.v1.md + case_approach_guide.v1.md), then the "
                        "assistant turn prefilled with the documents through applicability. Granite writes from "
                        "`kind: reasoning` on.",
                "added": added, "prefill": prefill, "text": _msgs_text(ep.messages)}
        if p.g.pair.relation == "not_governed":
            out["prompts"]["nocase"] = {"what": "Random arm (Peter's design): Granite with NO case (the -noref prompt), "
                                                "prefilled with the fixed F and K documents; its "
                                                "reasoning and verdict are spliced in after the not_governed "
                                                "applicability (no case_approach)."}
    except Exception as e:                                            # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {e}"
    return out
