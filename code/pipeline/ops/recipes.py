"""Recipes and the planner (OPERATORS-SPEC-v1 §Layers). An arm is a recipe: a list of operator steps. The planner expands
each step's batch-level arguments for the scenarios entering it, runs the jobs in threads, records every application
(code-built lineage via record.finish) and feeds the outputs to the next step.

Recipe file (YAML):
    name: same_domain_flip
    chain: [accepted]                 # which buckets feed the next step (default: accepted)
    # a step with `pass_skipped: true` feeds its skipped inputs (no-ops) on unchanged
    steps:
      - op: structural_edit
        args: {mode: flip, phi: each, realization: plain}
      - op: permute
        args: {target: options, order: balance}

Planner-expanded arguments:
    structural_edit.phi     each | first | random | <id>   (flip: would_change items whose then != V; target_f: would_not_change)
    frame_edit.option       each_nongold | random_nongold | <id>
    judgment_edit.target    auto | each | <id>
    permute.order           balance (gold position balanced over the batch, per option count) | random | {gold_to: k} | [..]
    surface_edit.setting    propose | {sketch_file: <md>, sister: A|B} | {subdomain, title, sketch}
"""
from __future__ import annotations

import json
import random
import time
import traceback
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

from pipeline.store import ROOT, Store

from .frame import drop_option
from .judgment import judgment_edit
from .permute import permute
from .record import finish, load_any
from .structural import structural_edit
from .surface import surface_edit

RUNS = ROOT / "results" / "ops" / "runs"
OPS = {"permute": permute, "surface_edit": surface_edit, "structural_edit": structural_edit,
       "frame_edit": lambda X, store, **a: drop_option(X, store, **{k: v for k, v in a.items() if k != "target"}),
       "judgment_edit": judgment_edit}


def _seed(*parts) -> int:
    import hashlib
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


def expand(step: dict, scens: list, seed: int = 0) -> list[tuple]:
    """-> [(X, kwargs)] for one step over the scenarios entering it."""
    op, a = step["op"], dict(step.get("args") or {})
    jobs = []
    if op == "structural_edit":
        kind = "would_change" if a.get("mode") == "flip" else "would_not_change"
        for X in scens:
            fc = X.case.flip_conditions
            items = [w.id for w in getattr(fc, kind) if kind != "would_change" or w.then != X.case.verdict.choice]
            pick = a.get("phi", "each")
            chosen = (items if pick == "each" else items[:1] if pick == "first"
                      else [random.Random(_seed(X.id, seed)).choice(items)] if pick == "random" and items else [pick] if pick in items else [])
            jobs += [(X, {**a, "phi": i}) for i in chosen]
    elif op == "frame_edit":
        for X in scens:
            non = [o for o in X.case.options if o != X.case.verdict.choice]
            pick = a.get("option", "random_nongold")
            chosen = (non if pick == "each_nongold" else [random.Random(_seed(X.id, seed)).choice(non)] if pick == "random_nongold" and non
                      else [pick] if pick in X.case.options else [])
            jobs += [(X, {**a, "option": o}) for o in chosen]
    elif op == "judgment_edit":
        for X in scens:
            t = a.get("target", "auto")
            ts = [o for o in X.case.options if o != X.case.verdict.choice] if t == "each" else [t]
            jobs += [(X, {**a, "target": x, "seed": seed}) for x in ts]
    elif op == "permute":
        order = a.get("order", "random")
        if order == "balance":
            by_n = defaultdict(list)
            for X in scens:
                by_n[len(X.case.options)].append(X)
            for n, xs in by_n.items():
                rng = random.Random(_seed("balance", n, seed))
                xs = sorted(xs, key=lambda s: s.id)
                targets = [(i % n) + 1 for i in range(len(xs))]
                rng.shuffle(targets)
                jobs += [(X, {**a, "order": {"gold_to": k}, "seed": seed}) for X, k in zip(xs, targets)]
        else:
            jobs += [(X, {**a, "seed": _seed(X.id, seed)}) for X in scens]
    elif op == "surface_edit":
        st = a.get("setting", "propose")
        for X in scens:
            if isinstance(st, dict) and st.get("sketch_file"):
                from pipeline.transfer.build import parse_sketch
                anchor = X.lineage.anchor or X.id
                sk = [s for s in parse_sketch(st["sketch_file"]) if s["anchor"] in (X.id, anchor)
                      and (not st.get("sister") or s["sister"] == st["sister"])]
                jobs += [(X, {**a, "setting": {k: s[k] for k in ("subdomain", "title", "sketch", "anchor_sketch", "sister", "sketch_file")}})
                         for s in sk]
            else:
                jobs += [(X, {**a, "seed": seed})]
    else:
        raise ValueError(f"unknown op {op}")
    return jobs


def run_job(store: Store, X, op: str, kwargs: dict, recipe: str, step_no: int) -> dict:
    t0 = time.time()
    try:
        r = OPS[op](X, store, **kwargs)
        r.args = {**r.args, "recipe": recipe, "recipe_step": step_no}
        row = finish(store, X, r)
    except Exception as e:                                               # noqa: BLE001
        row = {"op": op, "args": kwargs, "parent": X.id, "bucket": "error", "why": f"{type(e).__name__}: {str(e)[:300]}",
               "trace": traceback.format_exc()[-1500:]}
    row["seconds"] = round(time.time() - t0, 1)
    row["recipe"], row["recipe_step"] = recipe, step_no
    return row


def run_recipe(recipe: dict, inputs: list[str], store: Store | None = None, workers: int = 8, seed: int = 0,
               log: Path | None = None, dry: bool = False) -> dict:
    store = store or Store()
    name = recipe["name"]
    chain = set(recipe.get("chain") or ["accepted"])
    RUNS.mkdir(parents=True, exist_ok=True)
    log = log or RUNS / f"{name}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.jsonl"
    scens = [load_any(store, s) for s in inputs]
    summary = {"recipe": name, "inputs": len(scens), "log": str(log), "steps": []}
    for i, step in enumerate(recipe["steps"], 1):
        jobs = expand(step, scens, seed)
        if dry:
            summary["steps"].append({"step": i, "op": step["op"], "jobs": len(jobs),
                                     "examples": [(X.id, {k: v for k, v in kw.items() if k != "setting"}) for X, kw in jobs[:5]]})
            continue
        rows = []
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(run_job, store, X, step["op"], kw, name, i) for X, kw in jobs]
            for f in as_completed(futs):
                row = f.result()
                rows.append(row)
                with open(log, "a") as fh:
                    fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        summary["steps"].append({"step": i, "op": step["op"], "jobs": len(jobs), "buckets": dict(Counter(r["bucket"] for r in rows))})
        nxt = [r["id"] for r in rows if r.get("id") and r["bucket"] in chain]
        if step.get("pass_skipped"):       # a no-op (e.g. options already matched) passes its input on unchanged
            nxt += [r["parent"] for r in rows if r["bucket"] == "skipped" and r.get("parent")]
        scens = [load_any(store, s) for s in nxt]
        if not scens:
            break
    summary["outputs"] = [s.id for s in scens]
    return summary


def load_recipe(path: str) -> dict:
    r = yaml.safe_load(Path(path).read_text())
    if not r.get("name") or not r.get("steps"):
        raise ValueError("a recipe needs `name` and `steps`")
    return r
