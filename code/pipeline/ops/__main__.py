"""CLI for the scenario operators (context/OPERATORS-SPEC-v1.md).

    python -m pipeline.ops apply <op> --scenario ID [--args '{"mode": "flip", "phi": "flip1"}'] [--no-save]
    python -m pipeline.ops recipe <recipe.yaml> (--scenario ID ... | --inputs file.txt) [--workers 8] [--dry]
    python -m pipeline.ops analytics [--since 2026-11-11] [--out results/ops/ANALYTICS.md]
    python -m pipeline.ops migrate [--apply]
    python -m pipeline.ops grounding (--scenario ID ... | --inputs file.txt) [--window 12] [--workers 8]
    python -m pipeline.ops enqueue-review (--scenario ID ... | --inputs file.txt) [--source NAME]
        queue spot-check tasks for the console (/queue); answers go to data/labels/labels.jsonl
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pipeline.store import Store

from . import analytics, grounding, migrate
from .recipes import OPS, load_recipe, run_job, run_recipe
from .record import finish, load_any


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline.ops")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("apply")
    a.add_argument("op", choices=sorted(OPS))
    a.add_argument("--scenario", required=True)
    a.add_argument("--args", default="{}")
    a.add_argument("--no-save", action="store_true")
    r = sub.add_parser("recipe")
    r.add_argument("recipe")
    r.add_argument("--scenario", nargs="*", default=[])
    r.add_argument("--inputs")
    r.add_argument("--workers", type=int, default=8)
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--dry", action="store_true")
    n = sub.add_parser("analytics")
    n.add_argument("--since")
    n.add_argument("--out")
    m = sub.add_parser("migrate")
    m.add_argument("--apply", action="store_true")
    gr = sub.add_parser("grounding")
    gr.add_argument("--scenario", nargs="*", default=[])
    gr.add_argument("--inputs")
    gr.add_argument("--window", type=int, default=12)
    gr.add_argument("--workers", type=int, default=8)
    q = sub.add_parser("enqueue-review")
    q.add_argument("--scenario", nargs="*", default=[])
    q.add_argument("--inputs")
    q.add_argument("--source", default="manual")
    ns = ap.parse_args(argv)
    store = Store()

    if ns.cmd == "apply":
        X = load_any(store, ns.scenario)
        kw = json.loads(ns.args)
        if ns.no_save:
            res = OPS[ns.op](X, store, **kw)
            row = finish(store, X, res, save=False)
            row["scenario"] = res.scenario.dump() if res.scenario else None
            row["gates"], row["annotations"], row["delta"] = res.gates, res.annotations, res.delta
        else:
            row = run_job(store, X, ns.op, kw, "adhoc", 1)
        print(json.dumps(row, indent=1, ensure_ascii=False, default=str))
    elif ns.cmd == "recipe":
        ids = list(ns.scenario)
        if ns.inputs:
            ids += [l.split()[0] for l in Path(ns.inputs).read_text().splitlines() if l.strip() and not l.startswith("#")]
        if not ids:
            sys.exit("give --scenario or --inputs")
        print(json.dumps(run_recipe(load_recipe(ns.recipe), ids, store, ns.workers, ns.seed, dry=ns.dry), indent=1, default=str))
    elif ns.cmd == "analytics":
        text = analytics.report(analytics.collect(store, ns.since))
        if ns.out:
            Path(ns.out).parent.mkdir(parents=True, exist_ok=True)
            Path(ns.out).write_text(text)
        print(text)
    elif ns.cmd == "grounding":
        ids = list(ns.scenario)
        if ns.inputs:
            ids += [l.split()[0] for l in Path(ns.inputs).read_text().splitlines() if l.strip() and not l.startswith("#")]
        rows = grounding.run(store, ids, ns.window, ns.workers)
        from collections import Counter
        print(json.dumps({"scenarios": len(rows), "errors": sum(1 for r in rows if r.get("error")),
                          "labels": dict(Counter(f"{i['kind']}:{i['label']}" for r in rows for i in r.get("items", []))),
                          "out": str(grounding.OUT)}, indent=1, default=str))
    elif ns.cmd == "enqueue-review":
        from . import queue as Q
        ids = list(ns.scenario)
        if ns.inputs:
            ids += [l.split()[0] for l in Path(ns.inputs).read_text().splitlines() if l.strip() and not l.startswith("#")]
        if not ids:
            sys.exit("give --scenario or --inputs")
        out = []
        for sid in ids:
            load_any(store, sid)                       # fails loudly on an unknown id
            out.append(Q.enqueue_review(sid, source=ns.source))
        print(json.dumps({"queued": len(out), "tasks": out, "queue": str(Q.QUEUE)}, indent=1))
    elif ns.cmd == "migrate":
        rows = migrate.plan(store)
        print(json.dumps(migrate.summary(rows), indent=1))
        if ns.apply:
            print("migrated", migrate.apply(rows))


if __name__ == "__main__":
    main()
