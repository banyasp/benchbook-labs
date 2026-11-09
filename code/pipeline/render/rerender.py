"""Re-render live traces with the current render prompt and every gate on (2026-11-09: render.v4 + framing check).

For each scenario id: the live trace directory is moved to data/store/traces/_versions/<id>.<tag>-<ts>/ (kept, never
deleted), then pipeline.render.trace.render_one renders it again with the answer-leak and framing gates (both on by
default for the real renderer). A trace that still fails after the retries is NOT live (it goes to traces/_rejected/ as
usual) and the log says why; its old version stays in _versions/.

    PYTHONPATH=code .venv/bin/python -m pipeline.render.rerender --ids <file> --tag pre-render-v4 \\
        --log results/render/rerender-v4-<date>.jsonl
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pipeline.store import Store


def rerender_one(store: Store, sid: str, tag: str) -> dict:
    from .trace import render_one
    out = {"scenario": sid, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    try:
        if store.has_trace(sid):
            dst = store.root / "traces" / "_versions" / f"{sid}.{tag}-{time.strftime('%Y%m%d%H%M%S')}"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(store.trace_dir(sid)), str(dst))
            out["old"] = str(dst)
        r = render_one(store, sid)
        d = r.diagnostics
        out.update(final="ok" if d.get("status") == "ok" else "rejected", reason=d.get("reason"),
                   attempts=len(d.get("attempts") or []), words=d.get("words"),
                   framing=[{k: x.get(k) for k in ("kind", "message", "quote", "why")}
                            for x in (r.gates.get("framing") or {}).get("items", [])][:6],
                   answer_leak=[{k: x.get(k) for k in ("kind", "quote")}
                                for x in (r.gates.get("answer_leak") or {}).get("items", [])][:4])
    except Exception as e:                                   # noqa: BLE001
        out.update(final="error", error=f"{type(e).__name__}: {e}"[:300])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", required=True)
    ap.add_argument("--tag", default="pre-render-v4")
    ap.add_argument("--log", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv)
    ids = [l.strip() for l in Path(a.ids).read_text().splitlines() if l.strip() and not l.startswith("#")]
    log = Path(a.log)
    log.parent.mkdir(parents=True, exist_ok=True)
    done = ({json.loads(l)["scenario"] for l in log.read_text().splitlines()      # rejected / error are retried
             if l.strip() and json.loads(l).get("final") == "ok"} if log.exists() else set())
    todo = [s for s in dict.fromkeys(ids) if s not in done]
    store = Store()
    from collections import Counter
    c = Counter()
    with ThreadPoolExecutor(a.workers) as ex, open(log, "a") as fh:
        for r in ex.map(lambda s: rerender_one(store, s, a.tag), todo):
            fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
            fh.flush()
            c[r["final"]] += 1
            print(r["scenario"], r["final"], r.get("reason") or "", file=sys.stderr, flush=True)
    print(json.dumps(dict(c)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
