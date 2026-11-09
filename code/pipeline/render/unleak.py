"""Fix answer leaks (Peter, 2026-11-09: leaky traces are never used; edit them or regenerate them carefully).

For each scenario flagged by `pipeline.render.answer_leak` (v2, role-aware):
  1. fact-level leak: rewrite ONLY the flagged facts so they state what was true or known before the decision point,
     dropping that this decision was made (by the agent / its role / its decider) or what happened after it. Fact ids,
     kinds, statuses and every reference (considerations, fact_spans) are unchanged. The old scenario file is copied to
     <family>/versions/<id>.<ts>.yaml first; the edit is a provenance step `unleak` (model, prompt hash, old text).
  2. re-render the trace with the answer-leak gate on (render.trace leak_check; a leak is fed back and retried).
  3. re-check facts + trace. Clean -> the trace is live in the store. Still leaking -> the trace is moved back to
     traces/_leaked/ and the scenario is reported (it stays out of every grid).

    PYTHONPATH=code .venv/bin/python -m pipeline.render.unleak --ids <file> --log results/allpairs/unleak-<date>.jsonl
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bench.schema.pipeline import sha256_text
from pipeline.store import Store

from . import answer_leak as AL
from .util import extract_json, make_step

FIX_SYSTEM = """You edit facts in a decision scenario used to evaluate an AI agent. The agent acts in the stated ROLE for
the stated DECIDER and must answer the QUESTION. Some facts give the decision away: they say that this decision was
already made or carried out (by the agent, its role or its decider), or describe what happened after it.

Rewrite ONLY the listed facts so that each states what was true or known BEFORE the decision point, with the decision
left open. Keep every other detail of the fact (who, what, when, numbers, findings, assessments, constraints) and its
meaning for the decision; remove only the part that reports the decision or its aftermath. If a fact is nothing but the
decision, restate the underlying situation it refers to (e.g. "The commander declined the pilots' offer of a show of
force" -> "The pilots offered a show of force to disperse the people on the sandbank"). Do not add recommendations,
new facts or hints about the right course. Same register and length as the original.

Return one JSON object only: {"<fact id>": "<rewritten fact>", ...} with exactly the listed ids."""


def fix_facts(store: Store, sid: str, items: list[dict], llm=None) -> dict:
    from bench.models import complete
    llm = llm or (lambda m: complete("answer_leak_checker", m, stage="unleak"))
    T = store.scenario(sid)
    c = T.case
    by_id = {f.id: f for f in c.facts}
    ids = [x["id"] for x in items if x.get("id") in by_id]
    if not ids:
        return {"edited": [], "note": "no valid fact ids in the leak record"}
    opts = "\n".join(f"{oid}: {o.do}" for oid, o in c.options.items())
    facts = "\n".join(f"{f.id}: {f.fact}" for f in c.facts)
    why = "\n".join(f"{x['id']}: {x.get('why')}" for x in items if x.get("id") in by_id)
    user = (f"AGENT: {c.agent}\nAGENT ROLE: {c.agent_role}\nDECIDER: {c.decider}\nQUESTION: {c.question}\n\n"
            f"COURSES OF ACTION:\n{opts}\n\nALL FACTS:\n{facts}\n\nFACTS TO REWRITE (and why they leak):\n{why}")
    raw = llm([{"role": "system", "content": FIX_SYSTEM}, {"role": "user", "content": user}])
    obj = extract_json(raw)
    if set(obj) != set(ids):
        raise ValueError(f"fix returned ids {sorted(obj)} != {sorted(ids)}")
    # keep the old file
    p = store.scenario_path(T)
    vdir = p.parent / "versions"
    vdir.mkdir(exist_ok=True)
    shutil.copy2(p, vdir / f"{p.stem}.{time.strftime('%Y%m%d-%H%M%S')}.yaml")
    old = {i: by_id[i].fact for i in ids}
    for i in ids:
        by_id[i].fact = str(obj[i]).strip()
    step = make_step(f"unleak-{time.strftime('%Y%m%d%H%M%S')}", "unleak", "answer_leak_checker",
                     ("unleak", "v1", sha256_text(FIX_SYSTEM)[:12]),
                     {"facts": ",".join(ids)}, notes=json.dumps({"old": old}, ensure_ascii=False)[:4000])
    T.provenance.steps.append(step)
    for i in ids:
        T.provenance.fields[f"case.facts.{i}.fact"] = step.id
        if f"case.facts.{i}.fact" not in T.provenance.authored:
            T.provenance.authored.append(f"case.facts.{i}.fact")     # model-written text, no source span for the edit
    store.save_scenario(T)
    return {"edited": ids, "old": old, "new": {i: by_id[i].fact for i in ids}}


def fix_one(store: Store, rec: dict) -> dict:
    from .trace import render_one
    sid = rec["scenario"]
    out = {"scenario": sid, "where": rec.get("where"), "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    try:
        if rec.get("facts"):
            out["fact_fix"] = fix_facts(store, sid, rec["facts"])
        r = render_one(store, sid, leak_check=AL.trace_leaks)
        out["render"] = r.diagnostics.get("status")
        out["render_reason"] = r.diagnostics.get("reason")
        if out["render"] != "ok":
            out["final"] = "dropped (render)"
            return out
        chk = AL.check_one(store, sid)
        out["recheck"] = {k: chk.get(k) for k in ("leak", "where", "facts", "trace", "error")}
        if chk.get("leak") or chk.get("error"):
            src = store.trace_dir(sid)
            dst = store.root / "traces" / "_leaked" / f"{sid}.recheck-{time.strftime('%Y%m%d%H%M%S')}"
            shutil.move(str(src), str(dst))
            out["final"] = "dropped (still leaks)"
        else:
            out["final"] = "fixed"
    except Exception as e:                                   # noqa: BLE001
        out["final"] = "error"
        out["error"] = f"{type(e).__name__}: {e}"[:300]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--leaks", default="results/allpairs/answer-leak-v2-20261109.jsonl")
    ap.add_argument("--ids", help="only these scenario ids (file)")
    ap.add_argument("--log", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv)
    recs = {}
    for line in Path(a.leaks).read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            if r.get("leak"):
                recs[r["scenario"]] = r
    if a.ids:
        want = {l.strip() for l in Path(a.ids).read_text().splitlines() if l.strip() and not l.startswith("#")}
        recs = {k: v for k, v in recs.items() if k in want}
    log = Path(a.log)
    done = ({json.loads(l)["scenario"] for l in log.read_text().splitlines()
             if l.strip() and json.loads(l).get("final") != "error"} if log.exists() else set())   # errors are retried
    todo = [r for s, r in recs.items() if s not in done]
    store = Store()
    from collections import Counter
    c = Counter()
    with ThreadPoolExecutor(a.workers) as ex, open(log, "a") as fh:
        for r in ex.map(lambda x: fix_one(store, x), todo):
            fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
            fh.flush()
            c[r["final"]] += 1
            print(r["scenario"], r["final"], file=sys.stderr, flush=True)
    print(json.dumps(dict(c)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
