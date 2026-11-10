"""Manifest of an eval dataset: which scenarios, traces, cases and answer keys a cell list uses (2026-11-10).

Reads a cells file (eval.transfer_cells output: [{x1, x2, arm}]) and writes
  <out>/<name>.manifest.json  machine-readable: per X1 its scenario file, trace, answer key (gold option id + text,
                              all options), metadata, and every cell (arm, X2, X2's file, X2's verdict as an X1 option);
                              sha256 of every file, so a later run can check it used the same data
  <out>/<name>.md             readable summary: counts, the X1 table, and the store-wide context
Deterministic; no LLM.

    PYTHONPATH=code .venv/bin/python -m eval.analysis.dataset_manifest --name pilot2 \\
        --cells results/transfer/pilot2/cells.json --out measurements/datasets --notes measurements/datasets/pilot2.notes.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def main(argv=None):
    from pipeline.store import Store
    from eval.transfer_report import case_verdict_as_x1
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True)
    ap.add_argument("--cells", required=True)
    ap.add_argument("--out", default="measurements/datasets")
    ap.add_argument("--notes", help="markdown with the provenance / selection story, prepended to the summary")
    a = ap.parse_args(argv)
    st = Store()
    root = st.root
    cells = json.loads(Path(a.cells).read_text())
    x1s = list(dict.fromkeys(c["x1"] for c in cells))
    out = {"name": a.name, "cells_file": a.cells, "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "store": str(root), "x1": []}
    for x in x1s:
        T = st.scenario(x)
        c = T.case
        sp = st.scenario_path(x)
        td = st.trace_dir(x)
        tj = td / "trace.json"
        rec = {"id": x, "title": getattr(c, "title", None), "family": T.family, "domain": T.domain,
               "content_domain": getattr(T, "content_domain", None), "split": T.split, "held_out": bool(T.held_out),
               "status": T.status, "scenario_file": str(sp.relative_to(root.parent.parent)), "scenario_sha": sha(sp),
               "trace_dir": str(td.relative_to(root.parent.parent)),
               "trace_sha": sha(tj) if tj.exists() else None,
               "trace_mtime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(tj.stat().st_mtime)) if tj.exists() else None,
               "question": c.question, "options": {k: o.do for k, o in c.options.items()},
               "gold": c.verdict.choice, "n_facts": len(c.facts), "n_considerations": len(c.considerations),
               "cells": []}
        for cl in cells:
            if cl["x1"] != x:
                continue
            X2 = st.scenario(cl["x2"])
            p2 = st.scenario_path(cl["x2"])
            rec["cells"].append({"arm": cl["arm"], "x2": cl["x2"], "x2_file": str(p2.relative_to(root.parent.parent)),
                                 "x2_sha": sha(p2), "x2_domain": X2.domain,
                                 "x2_verdict_as_x1_option": None if cl["arm"] in ("self", "decoy")
                                 else case_verdict_as_x1(st, cl["x2"]).replace("LIVE-", "")})
        out["x1"].append(rec)
    o = Path(a.out)
    o.mkdir(parents=True, exist_ok=True)
    (o / f"{a.name}.manifest.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))

    arms = Counter(cl["arm"] for cl in cells)
    scen = list((root / "scenarios").glob("*/*.yaml"))
    live = [p for p in (root / "traces").glob("*/trace.yaml")]
    rej = list((root / "traces" / "_rejected").glob("*")) if (root / "traces" / "_rejected").exists() else []
    L = [f"# Dataset: {a.name}", "", f"Generated {out['generated']} by `code/eval/analysis/dataset_manifest.py` from "
         f"`{a.cells}`. Machine-readable manifest: `{a.name}.manifest.json` (every file path and a sha256 prefix).", ""]
    if a.notes and Path(a.notes).exists():
        L += [Path(a.notes).read_text().strip(), ""]
    L += ["## Contents", "",
          f"- {len(x1s)} live scenarios X1 (each with its trace and answer key); cells: "
          + ", ".join(f"{k} {v}" for k, v in arms.items()) + f"; plus the no-case arm for every X1.",
          f"- Domains: " + ", ".join(f"{k} {v}" for k, v in Counter(r['domain'] for r in out['x1']).most_common()) + ".",
          f"- Splits: " + ", ".join(f"{k} {v}" for k, v in Counter(r['split'] for r in out['x1']).items())
          + f"; held out: {sum(r['held_out'] for r in out['x1'])}.",
          f"- Options per X1: " + ", ".join(f"{k} options: {v}" for k, v in sorted(Counter(len(r['options']) for r in out['x1']).items()))
          + f"; gold position: " + ", ".join(f"{k}: {v}" for k, v in sorted(Counter(list(r['options']).index(r['gold']) + 1 for r in out['x1']).items())) + ".",
          "", "## Where things are", "",
          "- **Scenario** (facts, question, options, the SME case = considerations, weighing, verdict, flip conditions; "
          "the answer key is `case.verdict.choice`): `data/store/scenarios/<family>/<id>.yaml` (schema: "
          "`code/bench/schema/pipeline.py` `Scenario`, `code/bench/schema/case.py` `Case`).",
          "- **Trace** (what the agent sees): `data/store/traces/<id>/trace.json` (messages) and `trace.yaml` (span map:"
          " where each fact and option is realized). Older versions: `data/store/traces/_versions/`.",
          "- **Served case** for a cell: the X2 scenario's `case`, served as REF1 (the X2 file below).",
          "", "## X1 scenarios", "",
          "| # | X1 | domain | split | options | gold | self | transfer | flip | decoy |", "|---|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(out["x1"], 1):
        n = Counter(c["arm"] for c in r["cells"])
        L.append(f"| {i} | `{r['id']}` — {r['title'] or ''} | {r['domain']} | {r['split']} | {len(r['options'])} | "
                 f"{r['gold']} | {n['self']} | {n['transfer']} | {n['flip']} | {n['decoy']} |")
    L += ["", "## Store-wide context (at generation time)", "",
          f"- Scenario files in `data/store/scenarios/`: {len(scen)} in {len({p.parent for p in scen})} family folders "
          "(all sources, all statuses, sisters and flips included).",
          f"- Live traces: {len(live)}; rejected renders (`traces/_rejected/`): {len(rej)}.",
          "- Other pools: `data/store/transfer-hard/` (hard sisters, kept for later), `data/store/transfer-rejected/`."]
    (o / f"{a.name}.md").write_text("\n".join(L) + "\n")
    print(f"wrote {o / (a.name + '.manifest.json')} and {o / (a.name + '.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
