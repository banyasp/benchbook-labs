"""Batch analytics for the operator pipeline (OPERATORS-SPEC-v1 §Batch analytics; Peter: observability first). Read-only.

Per (op, mode): outputs by bucket, gate-failure counts, annotation rates; and over accepted outputs the drift metrics
(gold position, option count and length spread, supporting facts for the gold vs the other options, hand-up share of
golds, fact and consideration counts, gold tier). Run logs (results/ops/runs/*.jsonl) add skips, writer failures and
errors, which never reach the store. Flags drift; never deletes anything.

    python -m pipeline.ops analytics [--since 2026-11-11] [--out results/ops/ANALYTICS.md]
"""
from __future__ import annotations

import json
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from pipeline.store import ROOT, Store

HANDUP = {"ask", "refuse"}


def _iter_outputs(store: Store, since: str | None):
    dirs = [(p, "store") for p in (store.root / "scenarios").glob("*/*.yaml")]
    dirs += [(p, "held") for b in ("hard", "rejected") for p in (store.root / "held" / b).glob("*.yaml")]
    for p, where in dirs:
        d = yaml.safe_load(p.read_text())
        steps = (d.get("lineage") or {}).get("steps") or []
        if not steps:
            continue
        last = steps[-1]
        if since and str(last.get("ts", "")) < since:
            continue
        yield d, last, where


def drift(case: dict) -> dict:
    gold = case["verdict"]["choice"]
    ids = list(case["options"])
    lens = [len(o["do"].split()) for o in case["options"].values()]
    support = Counter()
    for k in case["considerations"]:
        for o in k.get("favors", []):
            support[o] += len(k.get("facts", []))
    others = [support[o] for o in ids if o != gold]
    return {"gold_pos": ids.index(gold) + 1, "n_options": len(ids), "len_spread": round(max(lens) / max(1, min(lens)), 2),
            "gold_len_rank": sorted(lens, reverse=True).index(len(case["options"][gold]["do"].split())) + 1,
            "support_gold": support[gold], "support_other_mean": (sum(others) / len(others)) if others else 0,
            "handup_gold": case["options"][gold]["move"] in HANDUP,
            "n_facts": len(case["facts"]), "n_considerations": len(case["considerations"])}


def collect(store: Store | None = None, since: str | None = None, runs_dir: Path | None = None) -> dict:
    store = store or Store()
    by = defaultdict(lambda: {"buckets": Counter(), "gate_fail": Counter(), "annot": Counter(), "drift": [], "tiers": Counter()})
    for d, step, where in _iter_outputs(store, since):
        key = f"{step['op']}" + (f"/{step['mode']}" if step.get("mode") else "")
        b = by[key]
        b["buckets"][step.get("bucket", "?")] += 1
        for g, v in (step.get("gates") or {}).items():
            if not v.get("pass", True):
                b["gate_fail"][g] += 1
        vs = (step.get("annotations") or {}).get("verdict_shift")
        if vs:
            b["annot"]["verdict_shift.run"] += 1
            b["annot"]["verdict_shift.informative"] += bool(vs.get("informative"))
            b["annot"]["verdict_shift.flag"] += bool(vs.get("flag"))
        if step.get("bucket") == "accepted":
            b["drift"].append(drift(d["case"]))
            b["tiers"][d.get("verdict_tier")] += 1
    runs = Counter()
    for p in sorted((runs_dir or ROOT / "results" / "ops" / "runs").glob("*.jsonl")):
        for line in p.read_text().splitlines():
            r = json.loads(line)
            if r.get("bucket") in ("skipped", "error") or (r.get("bucket") == "rejected" and not r.get("id")):
                key = f"{r['op']}" + (f"/{r['mode']}" if r.get("mode") else "")
                outcome = "writer_failed" if r["bucket"] == "rejected" else r["bucket"]
                runs[(key, outcome, (r.get("why") or "")[:60])] += 1
    return {"by": by, "runs": runs}


def report(data: dict) -> str:
    out = ["# Operator pipeline analytics", "",
           "Read-only (`python -m pipeline.ops analytics`). Drift metrics are over accepted outputs. Nothing here deletes data.", "",
           "| op/mode | accepted | hard | rejected | gate failures | verdict_shift flag / informative / run |", "|---|---|---|---|---|---|"]
    for k, b in sorted(data["by"].items()):
        gf = ", ".join(f"{g} {n}" for g, n in b["gate_fail"].most_common()) or "-"
        a = b["annot"]
        out.append(f"| {k} | {b['buckets']['accepted']} | {b['buckets']['hard']} | {b['buckets']['rejected']} | {gf} | "
                   f"{a['verdict_shift.flag']} / {a['verdict_shift.informative']} / {a['verdict_shift.run']} |")
    out += ["", "## Drift over accepted outputs", "",
            "| op/mode | n | gold position (per option count) | option length spread (median) | gold is longest | "
            "facts supporting gold vs others (mean) | hand-up golds | facts / considerations (mean) | tiers |",
            "|---|---|---|---|---|---|---|---|---|"]
    for k, b in sorted(data["by"].items()):
        ds = b["drift"]
        if not ds:
            continue
        pos = defaultdict(Counter)
        for x in ds:
            pos[x["n_options"]][x["gold_pos"]] += 1
        pos_s = "; ".join(f"{n}-opt: " + " ".join(f"{p}:{c[p]}" for p in sorted(c)) for n, c in sorted(pos.items()))
        out.append(f"| {k} | {len(ds)} | {pos_s} | {st.median(x['len_spread'] for x in ds):.2f} | "
                   f"{sum(x['gold_len_rank'] == 1 for x in ds)}/{len(ds)} | "
                   f"{st.mean(x['support_gold'] for x in ds):.1f} vs {st.mean(x['support_other_mean'] for x in ds):.1f} | "
                   f"{sum(x['handup_gold'] for x in ds)}/{len(ds)} | "
                   f"{st.mean(x['n_facts'] for x in ds):.1f} / {st.mean(x['n_considerations'] for x in ds):.1f} | "
                   f"{', '.join(f'{t} {n}' for t, n in b['tiers'].items())} |")
    if data["runs"]:
        out += ["", "## Not in the store (from run logs)", "", "| op/mode | outcome | reason | n |", "|---|---|---|---|"]
        for (k, b, why), n in sorted(data["runs"].items()):
            out.append(f"| {k} | {b} | {why} | {n} |")
    return "\n".join(out) + "\n"
