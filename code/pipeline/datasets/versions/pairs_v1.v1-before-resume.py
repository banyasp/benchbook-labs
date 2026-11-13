"""Pair dataset v1, built with the scenario operators (Peter, 2026-11-11).

Peter's rulings for v1: pilot ~100 anchors, then all; every arm (self, transfer, flipped transfer, same-domain flip,
would-not-change edit, revised C', neighbor control, random (another anchor's case; called decoy until 2026-11-11); drop option removed the same day); X1 (the live trace) is always an anchor,
derived scenarios are only served as cases (revisit for SFT/RL); decide <-> advise parked; leaky scenarios never used.

    python -m pipeline.datasets.pairs_v1 eligibility [--workers 16]      # data/datasets/pairs-v1/eligibility.jsonl
    python -m pipeline.datasets.pairs_v1 pilot [--n 100] [--seed 0]      # data/datasets/pairs-v1/pilot-anchors.txt
    python -m pipeline.datasets.pairs_v1 build --inputs <ids.txt> --tag pilot [--workers 6] [--arms transfer,...]
        runs every arm recipe (code/pipeline/ops/recipes/pairs_v1/*.yaml) on the anchors, all in ONE process so the
        id reservation lock is shared (separate processes could mint the same derived id); writes
        data/datasets/pairs-v1/build-<tag>.json (per-recipe summaries and run-log paths)
    python -m pipeline.datasets.pairs_v1 assemble --tag pilot [--seed 0]
        -> cells-<tag>.json (X1 anchor x served X2, per arm), attempts-<tag>.jsonl, manifest-<tag>.json

Eligibility ("quality" anchors): every check is recorded per anchor, pass or fail with reasons; nothing is deleted.
  structure   parses; 2-4 options; gold among them; >= 1 consideration
  leak        pipeline.render.answer_leak v4 (role-aware, frame + facts) on the scenario: no leak (Peter, 2026-11-09:
              leaky scenarios are never used as X1 or X2). An unparseable check fails closed.
  technique   pipeline.ingest.technique_check: no strip-severity hit
Recorded but not gating: split / held_out, domain, n options, hand-up gold, would_change items whose then != gold
(flip capacity), would_not_change items, existing trace and its trace-leak result.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from bench.schema.pipeline import Scenario
from pipeline.store import ROOT, Store

OUT = ROOT / "data" / "datasets" / "pairs-v1"
HANDUP = {"ask", "refuse"}


def anchors(store: Store) -> list[Path]:
    return [p for p in sorted((store.root / "scenarios").glob("*/*.yaml")) if not Scenario.load(p).lineage.parent]


def check_anchor(store: Store, p: Path) -> dict:
    from pipeline.ops import checks as CK
    from pipeline.render import answer_leak as AL
    S = Scenario.load(p)
    c = S.case
    gold = c.verdict.choice
    row = {"id": S.id, "file": str(p.relative_to(ROOT)), "family": S.family, "domain": S.domain, "split": S.split,
           "held_out": S.held_out, "n_options": len(c.options), "gold": gold,
           "handup_gold": c.options[gold].move in HANDUP if gold in c.options else None,
           "flip_items": [w.id for w in c.flip_conditions.would_change if w.then != gold],
           "noflip_items": [w.id for w in c.flip_conditions.would_not_change], "has_trace": store.has_trace(S.id),
           "checks": {}, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    errs = []
    if not 2 <= len(c.options) <= 4:
        errs.append(f"{len(c.options)} options")
    if gold not in c.options:
        errs.append("gold not among options")
    if not c.considerations:
        errs.append("no considerations")
    row["checks"]["structure"] = {"pass": not errs, "why": errs}
    row["checks"]["technique"] = CK.technique_gate(S)
    msgs = store.trace_json(S.id)["messages"] if row["has_trace"] else None
    try:
        lk = AL.check(S, msgs)
        bad = (lk.get("frame") or []) + (lk.get("facts") or [])
        row["checks"]["leak"] = {"pass": not bad, "check": "answer_leak v4-frame", "items": bad[:5]}
        if msgs is not None:
            row["trace_leak"] = {"leak": bool(lk.get("trace")), "items": (lk.get("trace") or [])[:5]}
    except Exception as e:                                                   # noqa: BLE001
        row["checks"]["leak"] = {"pass": False, "error": f"unparseable: {e}"[:200]}
    row["eligible"] = all(v.get("pass") for v in row["checks"].values())
    row["why_not"] = [k for k, v in row["checks"].items() if not v.get("pass")]
    return row


def eligibility(workers: int = 16) -> dict:
    store = Store()
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "eligibility.jsonl"
    done = {json.loads(l)["id"] for l in out.read_text().splitlines()} if out.exists() else set()
    todo = [p for p in anchors(store) if Scenario.load(p).id not in done]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(check_anchor, store, p) for p in todo]
        for f in as_completed(futs):
            row = f.result()
            with open(out, "a") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    rows = [json.loads(l) for l in out.read_text().splitlines()]
    return {"anchors": len(rows), "eligible": sum(r["eligible"] for r in rows),
            "fails": dict(Counter(k for r in rows for k in r["why_not"])), "out": str(out)}


def pilot(n: int = 100, seed: int = 0) -> dict:
    """Stratified pilot: eligible anchors, one per family at most, spread over domain x split in proportion to the pool,
    at least one per stratum when possible."""
    rows = [json.loads(l) for l in (OUT / "eligibility.jsonl").read_text().splitlines()]
    pool = [r for r in rows if r["eligible"]]
    rng = random.Random(seed)
    by_fam = defaultdict(list)
    for r in pool:
        by_fam[r["family"]].append(r)
    one = [rng.choice(sorted(v, key=lambda r: r["id"])) for _, v in sorted(by_fam.items())]
    strata = defaultdict(list)
    for r in one:
        strata[(r["domain"], r["split"])].append(r)
    for v in strata.values():
        rng.shuffle(v)
    quota = {k: max(1, round(n * len(v) / len(one))) for k, v in strata.items()}
    picked = [r for k, v in sorted(strata.items()) for r in v[:quota[k]]]
    rng.shuffle(picked)
    picked = sorted(picked[:n], key=lambda r: r["id"])
    path = OUT / "pilot-anchors.txt"
    path.write_text("# pairs-v1 pilot anchors (stratified by domain x split, one per family; seed %d)\n" % seed
                    + "\n".join(r["id"] for r in picked) + "\n")
    return {"pool_eligible": len(pool), "families": len(one), "picked": len(picked), "out": str(path),
            "by_split": dict(Counter(r["split"] for r in picked)), "by_domain": dict(Counter(r["domain"] for r in picked)),
            "n_options": dict(Counter(r["n_options"] for r in picked)), "with_trace": sum(r["has_trace"] for r in picked)}


RECIPES = ROOT / "code" / "pipeline" / "ops" / "recipes" / "pairs_v1"


def build(inputs: str, tag: str, workers: int = 6, arms: list[str] | None = None, seed: int = 0) -> dict:
    from pipeline.ops.recipes import load_recipe, run_recipe
    ids = [l.split()[0] for l in Path(inputs).read_text().splitlines() if l.strip() and not l.startswith("#")]
    files = sorted(RECIPES.glob("*.yaml"))
    if arms:
        files = [f for f in files if f.stem in arms]
    store = Store()
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=len(files)) as ex:
        futs = {ex.submit(run_recipe, load_recipe(str(f)), ids, store, workers, seed): f.stem for f in files}
        res = {futs[f]: f.result() for f in as_completed(futs)}
    out = {"tag": tag, "inputs": inputs, "n_inputs": len(ids), "seed": seed, "workers": workers,
           "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)), "seconds": round(time.time() - t0),
           "recipes": res}
    (OUT / f"build-{tag}.json").write_text(json.dumps(out, indent=1, default=str))
    return out


# Which recipe step's output is served as which arm. drop_option is not an arm (Peter, 2026-11-11: it only shrinks
# the choice set and makes guessing easier); its earlier outputs stay on disk but never enter cells.
ARM_STEPS = {"transfer": [("transfer", 3), ("transfer_flip", 5)], "same_domain_flip": [("same_domain_flip", 2)],
             "noflip": [("noflip", 2)], "revised": [("revised", 2)], "neighbor": [("neighbor", 3)]}
ARMS = ["self", "transfer", "transfer_flip", "same_domain_flip", "noflip", "revised", "neighbor", "random"]


def _step_outputs(rows: list[dict], steps: list[dict], k: int) -> list[dict]:
    """The rows whose scenario leaves step k (1-based) of a recipe: accepted outputs, plus the inputs of skipped
    no-ops when the step has pass_skipped (the same rule recipes.run_recipe uses)."""
    out = [{"x2": r["id"], "row": r} for r in rows if r["recipe_step"] == k and r["bucket"] == "accepted" and r.get("id")]
    if steps[k - 1].get("pass_skipped"):
        out += [{"x2": r["parent"], "row": r} for r in rows if r["recipe_step"] == k and r["bucket"] == "skipped"]
    return out


def assemble(tag: str, seed: int = 0) -> dict:
    """build-<tag>.json + the recipe run logs -> cells-<tag>.json (one cell per X1 anchor x served X2) and
    attempts-<tag>.jsonl (every operator application, with its anchor resolved, for the console's per-anchor view).

    Cell: X1 = the anchor (live trace), X2 = the served case. Each cell carries its own answer key (`key`, an X1
    option id, and `key_source`). It is X1's gold for every arm except **revised**: C' has X1's facts and
    considerations with the weights edited, so a model that faithfully extends the served case reaches C''s verdict;
    that is the online-edit test (R54), and the key is C''s gold mapped onto X1's options by option text (Peter,
    2026-11-11, caught that a single X1 key would mark every faithful revised reply wrong). An eval over these cells
    must score against `key`, not against eval.allpairs' X1-only key."""
    from pipeline.ops.recipes import load_recipe
    store = Store()
    b = json.loads((OUT / f"build-{tag}.json").read_text())
    inp = Path(b["inputs"]) if Path(b["inputs"]).is_absolute() else ROOT / b["inputs"]
    ids = [l.split()[0] for l in inp.read_text().splitlines() if l.strip() and not l.startswith("#")]
    anchors_set = set(ids)
    logs = {name: [json.loads(l) for l in Path(v["log"]).read_text().splitlines() if l.strip()]
            for name, v in b["recipes"].items()}
    parent = {r["id"]: r["parent"] for rs in logs.values() for r in rs if r.get("id")}

    def anchor_of(x):
        seen = 0
        while x not in anchors_set and x in parent and seen < 20:
            x, seen = parent[x], seen + 1
        return x if x in anchors_set else None

    def chain_of(x):
        ch = [x]
        while ch[-1] not in anchors_set and ch[-1] in parent:
            ch.append(parent[ch[-1]])
        return list(reversed(ch))

    attempts = []
    for name, rs in logs.items():
        for r in rs:
            attempts.append({"recipe": name, "arm_excluded": name not in ARM_STEPS, "anchor": anchor_of(r["parent"]),
                             "step": int(r["recipe_step"]), "op": r["op"], "mode": r.get("mode"), "parent": r["parent"],
                             "id": r.get("id"), "bucket": r["bucket"], "why": r.get("why"),
                             "args": {k: v for k, v in (r.get("args") or {}).items()
                                      if k in ("mode", "phi", "target", "order", "option", "realization")}})
    gold = {}

    def gold_of(x):
        if x not in gold:
            S = store.scenario(x)
            gold[x] = S.case.verdict.choice
        return gold[x]

    cells = []
    for name, rs in logs.items():
        if name not in ARM_STEPS:
            continue
        steps = load_recipe(str(RECIPES / f"{name}.yaml"))["steps"]
        for arm, k in ARM_STEPS[name]:
            for o in _step_outputs(rs, steps, k):
                a = anchor_of(o["x2"])
                if a is None:
                    continue
                ch = chain_of(o["x2"])
                flip_row = next((x for x in attempts if x["id"] in ch and x["op"] == "structural_edit"), None)
                tgt = (flip_row or {}).get("args", {}).get("target")
                cells.append({"arm": arm, "x1": a, "x2": o["x2"], "chain": ch,
                              "phi": tgt.get("phi") if isinstance(tgt, dict) else None})
    # "random" arm (Peter 2026-11-11: renamed from "decoy"; nothing checks the drawn case is irrelevant, so it is a
    # random other case, not a guaranteed decoy). The seed string keeps the old name so draws stay reproducible.
    rng = random.Random(f"pairs-v1|decoy|{seed}")
    meta = {x: store.scenario(x) for x in ids}
    for x in ids:
        cells.append({"arm": "self", "x1": x, "x2": x, "chain": [x], "phi": None})
        pool = [y for y in ids if meta[y].family != meta[x].family and meta[y].domain != meta[x].domain] or \
               [y for y in ids if meta[y].family != meta[x].family]
        d = rng.choice(sorted(pool))
        cells.append({"arm": "random", "x1": x, "x2": d, "chain": [d], "phi": None})
    for c in cells:
        c["x1_gold"], c["x2_gold"] = gold_of(c["x1"]), gold_of(c["x2"])
        c["x1_has_trace"] = store.has_trace(c["x1"])
        c["key"], c["key_source"] = c["x1_gold"], "x1_gold"
        if c["arm"] == "revised":
            A, B = store.scenario(c["x1"]).case, store.scenario(c["x2"]).case
            by_text = {o.do: k for k, o in A.options.items()}
            c["key"] = by_text.get(B.options[c["x2_gold"]].do)
            c["key_source"] = "x2_revised_gold (C' verdict mapped to X1 options by text)" if c["key"] else "UNMAPPED"
    cells.sort(key=lambda c: (c["x1"], ARMS.index(c["arm"]), c["x2"]))
    for i, c in enumerate(cells):
        c["cell"] = f"PV1-{tag}-{i:05d}"
    (OUT / f"cells-{tag}.json").write_text(json.dumps(cells, indent=1))
    with open(OUT / f"attempts-{tag}.jsonl", "w") as fh:
        for a in attempts:
            fh.write(json.dumps(a, ensure_ascii=False) + "\n")
    man = {"dataset": "pairs-v1", "tag": tag, "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "build": f"data/datasets/pairs-v1/build-{tag}.json", "inputs": b["inputs"], "n_anchors": len(ids),
           "cells": len(cells), "by_arm": {a: sum(c["arm"] == a for c in cells) for a in ARMS},
           "anchors_with_trace": sum(store.has_trace(x) for x in ids), "random_seed": seed,
           "excluded_recipes": sorted(set(logs) - set(ARM_STEPS)),
           "key_sources": dict(Counter(c["key_source"] for c in cells)),
           "rules": ["X1 is always an anchor (Peter 2026-11-11; revisit for SFT/RL)",
                     "answer key per cell (`key`): X1 gold, except revised = C' gold mapped onto X1 options (online-edit test, R54; Peter 2026-11-11)",
                     "drop_option excluded (Peter 2026-11-11)", "decide<->advise parked",
                     "random: another pilot anchor drawn at random (different family and, when possible, different domain); not checked for irrelevance, so not called a decoy (Peter 2026-11-11)"]}
    (OUT / f"manifest-{tag}.json").write_text(json.dumps(man, indent=1))
    return man


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline.datasets.pairs_v1")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("eligibility")
    e.add_argument("--workers", type=int, default=16)
    pl = sub.add_parser("pilot")
    pl.add_argument("--n", type=int, default=100)
    pl.add_argument("--seed", type=int, default=0)
    b = sub.add_parser("build")
    b.add_argument("--inputs", required=True)
    b.add_argument("--tag", required=True)
    b.add_argument("--workers", type=int, default=6)
    b.add_argument("--arms")
    b.add_argument("--seed", type=int, default=0)
    s = sub.add_parser("assemble")
    s.add_argument("--tag", required=True)
    s.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    if a.cmd == "assemble":
        res = assemble(a.tag, a.seed)
    elif a.cmd == "build":
        res = build(a.inputs, a.tag, a.workers, a.arms.split(",") if a.arms else None, a.seed)
    else:
        res = eligibility(a.workers) if a.cmd == "eligibility" else pilot(a.n, a.seed)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
