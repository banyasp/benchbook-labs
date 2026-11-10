"""Compare transfer-pilot runs that differ only in model or reasoning mode (2026-11-10, Peter: "allow Granite to think
before it samples ... an apples-to-apples comparison against Luna").

Runs compared (same cells, same equities, same traces, k=8):
  pilot2        Granite 4.2 8B, mode C (the YAML steps ARE the thinking: prefill `kind: fact_enumeration` inside <think>)
  pilot2-modeA  Granite 4.2 8B, mode A (free prose thinking in <think>, then the YAML steps after </think>)
  pilot2-luna   GPT-6 Luna (hidden reasoning, effort medium, then the YAML steps)

Per run x arm: accuracy vs X1's key (mean over X1, family-bootstrap 95% CI), copy rate of the served case's verdict,
off-menu rate, relation mix. Flip arm only: does the verdict say `flips` with a `via` naming the flipped case's
would_change; which bucket the case's flipped consideration lands in; does the reply (YAML, or free thinking in mode A)
mention a flip condition at all. Paired per-X1 differences between runs on the same arm.

    PYTHONPATH=code .venv/bin/python -m eval.analysis.mode_compare --out results/transfer/MODE-COMPARE-<date>.md
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

import yaml

from bench.schema import parse_reply
from bench.schema.pipeline import Scenario
from eval.allpairs_report import fam_boot, ok, pct
from eval.core import read_samples
from eval.transfer_report import ARM_ORDER, case_verdict_as_x1

RUNS = [("pilot2", "Granite, YAML-only (mode C)"), ("pilot2-modeA", "Granite, think first (mode A)"),
        ("pilot2-luna", "Luna (hidden reasoning)")]
BUILD = "results/transfer/build-batch2-20261109.jsonl"
FLIPWORDS = re.compile(r"would[_ ]change|flip[_ ]?condition|REF1-flip|\bflip1\b", re.I)


def flip_info() -> dict:
    """flip id -> changed fact ids, flipped consideration ids, would_change ids (vs its unflipped sister)."""
    def load(p):
        return Scenario.model_validate(yaml.safe_load(open(p))).case
    info = {}
    for line in open(BUILD):
        r = json.loads(line)
        f = r.get("flip") or {}
        if r.get("bucket") == "accepted" and f.get("bucket") == "accepted":
            S, F = load(r["path"]), load(f["path"])
            of = {x.id: x.fact for x in S.facts}
            okc = {k.id: k for k in S.considerations}
            info[f["id"]] = dict(
                chf=[x.id for x in F.facts if of.get(x.id) != x.fact],
                chk=[k.id for k in F.considerations
                     if k.id in okc and (k.weight != okc[k.id].weight or set(k.favors) != set(okc[k.id].favors))],
                wc=[w.id for w in F.flip_conditions.would_change])
    return info


def bucket(doc, ref_id: str) -> str:
    if not isinstance(doc, dict):
        return "no_doc"
    for b in ("matched", "corresponding", "case_only"):
        for p in doc.get(b) or []:
            if ref_id in json.dumps(p):
                return b
    return "unmentioned"


def analyse(run: str, store, info) -> dict:
    d = Path("results/transfer") / run
    S = read_samples(d / "samples.jsonl")
    fam = {r["x1"]: r.get("x1_family") for r in S}
    acc = defaultdict(lambda: defaultdict(list))
    cp = defaultdict(lambda: defaultdict(list))
    c = defaultdict(Counter)
    cv = {}
    for r in S:
        arm = r["phase"]
        acc[arm][r["x1"]].append(ok(r["correct"]))
        k = c[arm]
        k["n"] += 1
        k["off_menu"] += bool(r.get("off_menu"))
        k["truncated"] += r.get("finish_reason") == "length"
        k["thinking_chars"] += (r.get("tokens") or {}).get("thinking_chars") or 0
        if arm in ("transfer", "flip") and r.get("x2"):
            cv.setdefault(r["x2"], case_verdict_as_x1(store, r["x2"]))
            cp[arm][r["x1"]].append(1.0 if r.get("translated_choice") == cv[r["x2"]] else 0.0)
        if arm not in ("transfer", "flip", "self", "decoy"):
            continue
        raw = (d / r["raw_path"]).read_text()
        p = parse_reply(raw)
        s = p.steps
        v = s.get("verdict") or {}
        k["rel:" + str(v.get("relation"))] += 1
        if arm != "flip" or r["x2"] not in info:
            continue
        inf = info[r["x2"]]
        k["flip_n"] += 1
        via_ok = bool(v.get("via")) and any("REF1-" + w in json.dumps(v.get("via")) for w in inf["wc"])
        k["flips with correct via"] += (v.get("relation") == "flips") and via_ok
        kb = [bucket(s.get("consideration_mapping"), "REF1-" + x) for x in inf["chk"]]
        k["flipped cons: " + next((b for b in ("case_only", "corresponding", "matched") if b in kb), "unmentioned")] += 1
        yaml_txt = json.dumps(s.get("reasoning") or {}) + json.dumps(s.get("applicability") or {})   # not the verdict: its own flip_conditions field always matches
        k["YAML mentions a flip condition"] += bool(FLIPWORDS.search(yaml_txt))
        m = re.search(r"<think>(.*?)(</think>|\Z)", raw, re.S)
        think = m.group(1) if m else ""
        prose = re.split(r"\bkind:\s*fact_enumeration", think)[0]       # free prose before any YAML draft
        k["free thinking mentions a flip condition"] += bool(FLIPWORDS.search(prose))
    return dict(acc=acc, cp=cp, c=c, fam=fam, n=len(S))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    from pipeline.store import Store
    store, info = Store(), flip_info()
    R = {run: analyse(run, store, info) for run, _ in RUNS if (Path("results/transfer") / run / "samples.jsonl").exists()}
    lab = dict(RUNS)
    L = ["# Reasoning-mode comparison on transfer pilot 2", "",
         "Same 28 anchors, same sisters, same traces, same equities; k=8 per cell. "
         + ", ".join(f"{lab[r]}: {R[r]['n']} samples" for r in R) + ".", "",
         "## Accuracy (vs X1's key) and copy rate", "",
         "| arm | " + " | ".join(lab[r] for r in R) + " |", "|---|" + "---|" * len(R)]
    for arm in ARM_ORDER:
        cells = []
        for r in R:
            x = R[r]
            if arm not in x["acc"]:
                cells.append("—")
                continue
            s = pct(fam_boot({i: mean(v) for i, v in x["acc"][arm].items()}, x["fam"]))
            if arm in x["cp"]:
                s += f"; copies {mean(mean(v) for v in x['cp'][arm].values()):.0%}"
            cells.append(s)
        L.append(f"| {arm} | " + " | ".join(cells) + " |")
    L += ["", "## Off-menu, truncation, thinking length", "",
          "| run | arm | n | off-menu | truncated | mean thinking chars |", "|---|---|---|---|---|---|"]
    for r in R:
        for arm in ARM_ORDER:
            k = R[r]["c"].get(arm)
            if k:
                n = k["n"]
                L.append(f"| {lab[r]} | {arm} | {n} | {k['off_menu']/n:.0%} | {k['truncated']/n:.0%} | "
                         f"{k['thinking_chars']/n:,.0f} |")
    L += ["", "## Relations declared (transfer, flip, self, decoy)", "",
          "| run | arm | follows | flips | distinguished | not_governed | none |", "|---|---|---|---|---|---|---|"]
    for r in R:
        for arm in ("self", "transfer", "flip", "decoy"):
            k = R[r]["c"].get(arm)
            if not k:
                continue
            m = sum(v for kk, v in k.items() if kk.startswith("rel:"))
            g = lambda x: f"{k.get('rel:' + x, 0) / m:.0%}" if m else "—"      # noqa: E731
            L.append(f"| {lab[r]} | {arm} | {g('follows')} | {g('flips')} | {g('distinguished')} | "
                     f"{g('not_governed')} | {g('None')} |")
    L += ["", "## Flip arm: does the model use the flip condition?", "",
          "| measure | " + " | ".join(lab[r] for r in R) + " |", "|---|" + "---|" * len(R)]
    keys = ["flips with correct via", "flipped cons: corresponding", "flipped cons: matched", "flipped cons: case_only",
            "flipped cons: unmentioned", "YAML mentions a flip condition", "free thinking mentions a flip condition"]
    for kk in keys:
        row = []
        for r in R:
            k = R[r]["c"]["flip"]
            row.append(f"{k[kk] / k['flip_n']:.0%}" if k["flip_n"] else "—")
        L.append(f"| {kk} | " + " | ".join(row) + " |")
    L += ["", "## Paired per-X1 differences between runs (same X1, same arm)", ""]
    pairs = [("pilot2-modeA", "pilot2"), ("pilot2-luna", "pilot2-modeA"), ("pilot2-luna", "pilot2")]
    for r1, r2 in pairs:
        if r1 not in R or r2 not in R:
            continue
        for arm in ARM_ORDER:
            A, B = R[r1]["acc"].get(arm, {}), R[r2]["acc"].get(arm, {})
            xs = [x for x in A if x in B]
            if xs:
                m, lo, hi = fam_boot({x: mean(A[x]) - mean(B[x]) for x in xs}, R[r1]["fam"])
                L.append(f"- {arm}: {lab[r1]} − {lab[r2]} = {100*m:+.0f} points [{100*lo:+.0f}, {100*hi:+.0f}] "
                         f"({len(xs)} X1s)")
    md = "\n".join(L) + "\n"
    Path(a.out).write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
