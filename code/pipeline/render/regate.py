"""Re-run the render gates on rejected traces without re-rendering (batch 2026-10-28, after the names-gate and
option-label fixes in gates.py). A rejected trace keeps its last attempt (trace.json with fact / option / recommendation
quotes); the spans are re-located from those quotes and the current gates re-run. Passing traces are promoted to the
trace store with `diagnostics.regated`; the rest stay in _rejected/ for a re-render.

    PYTHONPATH=code .venv/bin/python -m pipeline.render.regate [--dry]
"""
from __future__ import annotations

import argparse
import json
import sys

from bench.schema.pipeline import SpanMap, TraceRecord
from pipeline.store import Store

from .render import locate
from .trace import cards_for, channel_problems, locate_options, locate_recommendation, run_gates


def regate_one(store: Store, d) -> tuple[bool, dict]:
    rec = TraceRecord.load(d / "trace.yaml")
    tj = json.loads((d / rec.trace).read_text())
    T = store.scenario(rec.trace_scenario)
    msgs = [m for m in tj["messages"] if m.get("name") != "benchbook"]
    if not msgs:
        return False, {"reason": "no messages"}
    facts = [{"id": f["fact"], "quote": f["quote"], "message": f["message"], "realization": f.get("realization")}
             for f in tj.get("facts") or []]
    entries, miss = locate(msgs, facts, T)
    opts = [{"option": o["option"], "quote": o["quote"], "message": o["message"]} for o in tj.get("options") or []]
    opt_spans, opt_missing = locate_options(msgs, opts, T, rec.channels)
    r = tj.get("recommendation")
    robj = ({"option": str(r["option"]).rpartition("/")[2], "message": r["message"],
             "quote": msgs[r["message"]]["content"][r["start"]:r["end"]]} if isinstance(r, dict) else None)
    recspan, rec_probs = locate_recommendation(msgs, robj, rec.recommended_option, T.case)
    g = run_gates(msgs, T, entries, miss, opt_spans, opt_missing, rec_probs, channel_problems(msgs, opt_spans),
                  cards_for(store, T.id), rec.recommended_option)
    ok = all(v["pass"] for v in g.values())
    if not ok:
        return False, {k: v["pass"] for k, v in g.items()}
    diag = dict(rec.diagnostics, status="ok", regated="gates v3 (names FP fix, option-label run 12), no re-render",
                recommendation_span=recspan)
    diag.pop("reason", None)
    new = TraceRecord(trace_scenario=rec.trace_scenario, split=rec.split,
                      span_map=SpanMap(entries=entries, options=opt_spans, allowed=rec.span_map.allowed),
                      channels=rec.channels, recommended_option=rec.recommended_option, seed=rec.seed, gates=g,
                      diagnostics=diag, provenance=rec.provenance)
    new.provenance.step(id="render.regate", operator="render", notes=diag["regated"])
    return True, new.model_dump() | {"_trace_json": tj}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    store = Store()
    root = store.root / "traces" / "_rejected"
    n_ok = n = 0
    for d in sorted(p for p in root.iterdir() if (p / "trace.yaml").exists()) if root.exists() else []:
        if store.has_trace(d.name):
            continue
        n += 1
        try:
            ok, out = regate_one(store, d)
        except Exception as e:                                    # noqa: BLE001 - report and continue
            ok, out = False, {"error": f"{type(e).__name__}: {e}"[:200]}
        if ok:
            n_ok += 1
            tj = out.pop("_trace_json")
            if not a.dry:
                store.save_trace(TraceRecord.model_validate(out), tj)
        print(f"{d.name}: {'promoted' if ok else 'still rejected ' + json.dumps(out)}")
    print(f"regated {n}: promoted {n_ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
