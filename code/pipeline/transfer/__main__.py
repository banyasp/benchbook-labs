import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pipeline.store import Store

from .build import build_one, parse_sketch


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build cross-domain transfer sisters X2 (+ flips) from a sketch file.")
    ap.add_argument("--sketch", required=True, nargs="+")
    ap.add_argument("--log", default=f"results/transfer/build-{time.strftime('%Y%m%d')}.jsonl")
    ap.add_argument("--only", nargs="*", help="anchor numbers (e.g. 2 5 10) to build")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args(argv)
    sk = [s for f in a.sketch for s in parse_sketch(f)]
    if a.only:
        sk = [s for s in sk if str(s["anchor_no"]) in set(a.only)]
    store = Store()
    sk = [s for s in sk if _has(store, s["anchor"])]
    log = Path(a.log)
    log.parent.mkdir(parents=True, exist_ok=True)
    done = {json.loads(l)["sister"] for l in log.read_text().splitlines() if l.strip()} if log.exists() else set()
    from .build import sister_id
    sk = [s for s in sk if sister_id(s["anchor"], s["sister"]) not in done]
    if a.limit:
        sk = sk[:a.limit]
    print(f"{len(sk)} sisters to build", file=sys.stderr)

    def one(s):
        try:
            return build_one(store, s)
        except Exception as e:                                        # noqa: BLE001
            return {"sister": sister_id(s["anchor"], s["sister"]), "anchor": s["anchor"], "final": "error",
                    "error": f"{type(e).__name__}: {e}"[:500]}

    with ThreadPoolExecutor(a.workers) as ex, open(log, "a") as fh:
        for r in ex.map(one, sk):
            fh.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
            fh.flush()
            f = r.get("flip") or {}
            print(r["sister"], r.get("final"), r.get("bucket"), r.get("why"), "| flip:", f.get("bucket"), f.get("why"),
                  "| blind agrees:", (r.get("checks") or {}).get("blind", {}).get("agrees"), file=sys.stderr, flush=True)
    return 0


def _has(store, sid):
    try:
        store.scenario(sid)
        return True
    except Exception:                                                  # noqa: BLE001
        return False


if __name__ == "__main__":
    sys.exit(main())
