"""RL (GRPO) prompt pool with full answer keys (2026-11-15; Peter: one pool, filtered later by how often the SFT model
gets each prompt right).

One row per pairs-v1 cell: the exact model input (the same prompt SFT trained on: scaffold v4, mode B, pilot2
equities; checked byte-for-byte against the SFT rows where the cell has one) and the cell's FULL answer key
(bench.schema.AnswerKey from pipeline.project.gold_for over pipeline.sft.pairgold.pair_gold: options + choice,
relation, via, frame, facts, considerations, the fact / consideration / option maps, applicability). The reward
function is not decided (Peter): it will pick rows of scorers.rows from this key, so nothing here depends on it.

No LLM is called. Cells whose pair gold needs the fact aligner (transfer, neighbor, random, extension arms) reuse the
aligner output stored by SFT target generation (`--aligned`, default results/sft/gen1/write.jsonl); a cell without one
is skipped and reported, never re-aligned silently.

Scope (default = the gen1 SFT scope: the seven base arms, train split, served anchors train too). `--arms` widens it
(revised, extension arms: Peter's call).

    PYTHONPATH=code .venv/bin/python -m training.rl_data --out results/rl/pool-gen1 \
        [--cells data/datasets/pairs-v1/cells-full.json] [--arms self,neighbor,...] [--limit N]

Writes <out>/pool.jsonl, <out>/skipped.jsonl, <out>/config.json, <out>/report.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEN1_ARMS = ["self", "neighbor", "transfer", "noflip", "same_domain_flip", "transfer_flip", "random"]


def _jl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def eligible(cells: list[dict], arms: list[str], splits: list[str]) -> list[dict]:
    """Same rule as pipeline.sft.generate.select: X1 has a trace; X1, X2 and every chain member are in `splits` and
    not held out (derived scenarios are not in the eligibility file and share their anchor's split)."""
    el = {r["id"]: r for r in _jl(ROOT / "data/datasets/pairs-v1/eligibility.jsonl")}

    def ok(i):
        r = el.get(i)
        return r is None or (r["split"] in splits and not r["held_out"])

    return [c for c in cells if c["arm"] in arms and c["x1_has_trace"] and ok(c["x1"])
            and all(ok(i) for i in [c["x2"], *c["chain"]])]


def build_row(store, cell: dict, aligned: dict | None) -> dict:
    from pipeline.project.project import gold_for
    from pipeline.sft import targets as T
    from scorers.trl_adapter import served_column
    p = T.prepare(store, cell, aligned=aligned)
    _, key = gold_for(p.built.pair, store, C=p.built.C, T=p.built.T)
    key_json = key.model_dump(mode="json")
    prompt = p.ep.generation_prompt
    return {"id": f"rl-{cell['cell']}", "cell": cell["cell"], "arm": cell["arm"], "x1": cell["x1"], "x2": cell["x2"],
            "chain": cell["chain"], "format": "v4", "mode": "B", "policy": T.GRANITE,
            "prompt": prompt, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "key": key_json, "served": served_column(p.ep.served),   # scorers.trl_adapter.to_served reads it "key_sha256": hashlib.sha256(json.dumps(key_json, sort_keys=True).encode()).hexdigest(),
            "gold_choice": key.choice, "relation": key.relation, "via": key.via,
            "strategy": p.built.strategy, "pair_notes": p.built.notes,
            "aligner_source": "stored" if aligned else None}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--cells", default="data/datasets/pairs-v1/cells-full.json")
    ap.add_argument("--arms", default=",".join(GEN1_ARMS))
    ap.add_argument("--splits", default="train")
    ap.add_argument("--aligned", default="results/sft/gen1/write.jsonl", help="stored aligner outputs (jsonl by cell)")
    ap.add_argument("--sft-rows", default="results/sft/gen1/sft.jsonl", help="SFT rows: prompts must match byte-for-byte")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args(argv)
    from pipeline.store import Store
    store = Store()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    cells = json.loads((ROOT / a.cells).read_text())
    cells = cells["cells"] if isinstance(cells, dict) else cells
    arms, splits = a.arms.split(","), a.splits.split(",")
    todo = eligible(cells, arms, splits)[: a.limit]
    al = {r["cell"]: r.get("aligner") for r in _jl(ROOT / a.aligned)}
    sft_prompt = {r["cell"]: r["prompt"] for r in _jl(ROOT / a.sft_rows)}
    rows, skipped, mismatch = [], [], []
    t0 = time.time()
    for c in todo:
        try:
            r = build_row(store, c, al.get(c["cell"]))
        except Exception as e:                                       # noqa: BLE001  pair_gold Skip, missing aligner...
            skipped.append({"cell": c["cell"], "arm": c["arm"], "x1": c["x1"], "x2": c["x2"],
                            "reason": f"{type(e).__name__}: {e}"[:500]})
            continue
        sp = sft_prompt.get(c["cell"])
        r["sft_prompt_match"] = None if sp is None else (sp == r["prompt"])
        if sp is not None and sp != r["prompt"]:
            mismatch.append(c["cell"])
        rows.append(r)
    with open(out / "pool.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(out / "skipped.jsonl", "w") as f:
        for r in skipped:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    by = Counter(r["arm"] for r in rows)
    sk = Counter(r["arm"] for r in skipped)
    cfg = {"created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "cells_file": a.cells, "arms": arms,
           "splits": splits, "aligned": a.aligned, "sft_rows": a.sft_rows, "eligible": len(todo), "rows": len(rows),
           "skipped": len(skipped), "by_arm": dict(by), "skipped_by_arm": dict(sk),
           "sft_prompt_checked": sum(r["sft_prompt_match"] is not None for r in rows),
           "sft_prompt_mismatch": mismatch, "seconds": round(time.time() - t0, 1)}
    (out / "config.json").write_text(json.dumps(cfg, indent=1))
    L = [f"# RL pool `{a.out}` (generated by `code/training/rl_data.py`)", "",
         f"{len(rows)} rows from {len(todo)} eligible cells (arms {', '.join(arms)}; splits {', '.join(splits)}); "
         f"{len(skipped)} skipped. Prompts checked against SFT rows: {cfg['sft_prompt_checked']}, mismatches: "
         f"{len(mismatch)}.", "", "| arm | rows | skipped |", "|---|---|---|"]
    L += [f"| {arm} | {by.get(arm, 0)} | {sk.get(arm, 0)} |" for arm in arms]
    if skipped:
        L += ["", "Skip reasons:", ""] + [f"- {n} x {r}" for r, n in Counter(s["reason"][:120] for s in skipped).most_common(15)]
    (out / "report.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0 if not mismatch else 1


if __name__ == "__main__":
    sys.exit(main())
