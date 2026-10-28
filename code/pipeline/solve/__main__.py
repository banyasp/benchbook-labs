"""python -m pipeline.solve

Granite rejection sampling (default writer, design section 10):
  python -m pipeline.solve --all                                   # every train-split pair with a trace, not yet done
  python -m pipeline.solve --pairs-file ids.txt --redo              # one pair id per line
  python -m pipeline.solve --pair P-abc --judge stub                # offline judge (no Jev calls), for a dry run
  python -m pipeline.solve --all --rationalize-only                 # only pairs with zero accepted samples: the hinted pass
  python -m pipeline.solve --all --no-rationalize -n 4 --n-more 4 --config my.yaml
The gold-informed teacher (alternative writer):
  python -m pipeline.solve --writer teacher --pair P-abc [-n 3] [--equities pilot] [--require-touched]
"""
import argparse
import json
import sys
from pathlib import Path

from pipeline.store import DATA, ROOT, Store, write_json


def _teacher(a, st, pairs):
    from . import acceptance_report, solve_pair
    done = []
    for p in pairs:
        if not (p.trace or p.trace_ref):
            print(f"{p.id}: no trace, skipped (run render)", file=sys.stderr)
            continue
        if p.solve and not a.redo and not a.pair and any("/rs-" not in s.path for s in p.solve):
            done.append(p)
            continue
        p = solve_pair(p, st, a.equities, a.n, require_touched=a.require_touched)
        done.append(p)
        print(f"{p.id} [{p.intent}]: {sum(s.accepted for s in p.solve if '/rs-' not in s.path)}/{len(p.solve)} accepted", file=sys.stderr)
    rep = acceptance_report(done, st)
    write_json(st.root / "solve.acceptance.teacher.json", rep)      # solve.acceptance.json is the Granite-RS report
    print(json.dumps(rep, indent=1))


def _rs(a, st, pairs):
    from scorers.judge import CachedJudge, JevJudge, StubJudge
    from . import rs
    cfg = rs.RSConfig.load(a.config, n_first=a.n, n_more=a.n_more, n_rationalize=a.n_rationalize, max_tokens=a.max_tokens,
                           concurrency=a.concurrency, seed=a.seed, rationalize=False if a.no_rationalize else None,
                           examples=False if a.no_examples else None)
    todo = []
    for p in pairs:
        why = rs.eligible(p, None if a.split == "any" else a.split)
        if why and not a.pair:
            print(f"{p.id}: skipped ({why})", file=sys.stderr)
            continue
        done = rs.is_done(p, st)
        if a.rationalize_only:
            ok = done and not any(x.accepted for x in p.solve if "/rs-" in x.path) and not any(
                "/rs-r-" in x.path for x in p.solve)
            if not ok:
                continue
        elif done and not a.redo:
            continue
        todo.append(p)
    print(f"{len(todo)} pair(s) to sample ({len(pairs)} considered)", file=sys.stderr)
    judge = StubJudge() if a.judge == "stub" else CachedJudge(JevJudge(), path=a.judge_cache or ROOT / "results" / "judge_cache.sqlite")
    rs.run_rs(todo, st, judge, cfg, a.equities, log=lambda m: print(m, file=sys.stderr),
              rounds=("r",) if a.rationalize_only else None)
    rep = rs.write_acceptance(st, cfg)
    print(json.dumps(rep["overall"], indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline.solve")
    ap.add_argument("--writer", choices=["granite-rs", "teacher"], default="granite-rs")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pair")
    g.add_argument("--all", action="store_true")
    g.add_argument("--pairs-file", help="file with one pair id per line")
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--equities", help="equities yaml path or set id (default: the pair's `equities`)")
    ap.add_argument("-n", type=int, help="samples per pair (rs: first round, default 4; teacher: role samples)")
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--require-touched", action="store_true", help="teacher: also require the touched condition to be cited (R25)")
    # granite-rs
    ap.add_argument("--config", help="yaml overriding rs.config.yaml keys")
    ap.add_argument("--n-more", type=int)
    ap.add_argument("--n-rationalize", type=int)
    ap.add_argument("--max-tokens", type=int)
    ap.add_argument("--concurrency", type=int, help="vLLM requests in flight")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--split", default="train", help="split to sample (default train; `any` for all)")
    ap.add_argument("--no-rationalize", action="store_true")
    ap.add_argument("--rationalize-only", action="store_true")
    ap.add_argument("--no-examples", action="store_true", help="debug: omit the worked examples")
    ap.add_argument("--judge", choices=["jev", "stub"], default="jev")
    ap.add_argument("--judge-cache")
    a = ap.parse_args(argv)
    st = Store(a.data)
    if a.pair:
        pairs = [st.pair(a.pair)]
    elif a.pairs_file:
        pairs = [st.pair(l.strip()) for l in Path(a.pairs_file).read_text().split() if l.strip()]
    else:
        pairs = st.pairs()
    (_teacher if a.writer == "teacher" else _rs)(a, st, pairs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
