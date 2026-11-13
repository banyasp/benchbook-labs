"""SFT target generation at scale (Peter, 2026-11-13): the pipeline chosen in M13.

Per cell (pairs-v1, X1 = anchor with a trace, X1 and every served anchor in the train split, every arm but revised):

    write    Luna (sft_writer) writes the full target from the gold structure; the aligner (sft_aligner) supplies the
             fact/consideration maps where lineage has none (transfer, neighbor, random). Structure-checked. Bedrock.
    wv       non-random: base Granite writes W and V with Luna's reasoning + verdict as notes and the case_approach
             guidance, after the gold prefill F..applicability (targets.guided_rs, guide=True), k=2 per round, up to
             ROUNDS rounds. A sample is kept iff it passes check_reply AND Jev says its W supports the gold choice AND
             makes the same argument as Luna's. No sample kept -> Luna's own target (source "luna").
             random (not_governed): the same, except Granite gets the no-case prompt (T(X1) + E, no C(X2)) with
             Luna's no-case reasoning + verdict as notes and the F, K prefill; its W and V are spliced after the
             not_governed applicability (no case_approach). Same acceptance: gold choice, both gates, else Luna.
             (Until 2026-11-13 the random arm used Granite's own no-case choice; Peter: follow the answer key.)
    format   v4 (Peter, 2026-11-13): the verdict has no flip_conditions; the reply ends at the decision.
    assemble sft.jsonl rows: the exact model input (generation prompt, mode B, ends with the empty think block) and the
             completion (the target documents), plus chat messages, provenance and a sha256 per row.

    PYTHONPATH=code .venv/bin/python -m pipeline.sft.generate select   --run results/sft/gen1
    PYTHONPATH=code .venv/bin/python -m pipeline.sft.generate write    --run results/sft/gen1 --workers 16
    PYTHONPATH=code .venv/bin/python -m pipeline.sft.generate wv       --run results/sft/gen1 --workers 8 --follow
    PYTHONPATH=code .venv/bin/python -m pipeline.sft.generate assemble --run results/sft/gen1

Every stage is resumable (it skips cells already in its output) and appends one JSON line per cell with every raw
sample, so nothing is lost (observability rule). `wv --follow` runs alongside `write` and picks up new writes until
write.done appears.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import threading
import time
import traceback
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bench.models import ROOT

ARMS = ["self", "transfer", "transfer_flip", "same_domain_flip", "noflip", "neighbor", "random"]   # no revised (Peter)
ROUNDS = 2              # guided rounds of k=2 before falling back to Luna's text
K = 2
_lock = threading.Lock()


def _jl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def _append(path: Path, rec: dict):
    line = json.dumps(rec, ensure_ascii=False, default=str) + "\n"
    with _lock, open(path, "a") as f:
        f.write(line)


def _now() -> str:
    return time.strftime("%FT%TZ", time.gmtime())


# ---------------------------------------------------------------------------------------------- select
def select(run: Path, cells_file: str, splits: list[str]) -> list[dict]:
    """Cells for SFT: arm in ARMS; X1 has a trace; X1 and the served anchor (random arm: another anchor) are in
    `splits` and not held out, so no eval scenario appears in a training prompt. Derived scenarios (transfer, neighbor,
    flips) are built from X1 itself and share its split."""
    el = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "data/datasets/pairs-v1/eligibility.jsonl").open()}
    cells = json.load(open(ROOT / cells_file))

    def ok_anchor(i):
        r = el.get(i)
        return r is None or (r["split"] in splits and not r["held_out"])     # None: a derived scenario

    out = [c for c in cells if c["arm"] in ARMS and c["x1_has_trace"] and ok_anchor(c["x1"])
           and all(ok_anchor(i) for i in [c["x2"], *c["chain"]])]
    run.mkdir(parents=True, exist_ok=True)
    (run / "cells.json").write_text(json.dumps(out, indent=1))
    (run / "config.json").write_text(json.dumps({
        "cells_file": cells_file, "splits": splits, "arms": ARMS, "rounds": ROUNDS, "k": K,
        "pipeline": "M13 G+notes+guide (Peter 2026-11-13); random arm no-case W+V to the gold; format v4, mode B",
        "created": _now(), "by_arm": dict(Counter(c["arm"] for c in out))}, indent=1))
    return out


# ---------------------------------------------------------------------------------------------- write (Luna)
def write_stage(run: Path, workers: int):
    from pipeline.sft import targets as T
    from pipeline.store import Store
    store = Store()
    cells = json.load(open(run / "cells.json"))
    done = {r["cell"] for r in _jl(run / "write.jsonl")}
    (run / "write.done").unlink(missing_ok=True)

    def one(c):
        if c["cell"] in done:
            return
        t0 = time.time()
        try:
            p = T.prepare(store, c)
            w = T.write(p)
            rec = {"cell": c["cell"], "arm": c["arm"], "x1": c["x1"], "x2": c["x2"], "relation": p.g.pair.relation,
                   "choice": p.g.choice, "strategy": p.built.strategy, "gold_warnings": p.g.warnings,
                   "aligner": p.built.aligner, **{k: w[k] for k in ("try", "accepted", "reasons", "flags", "text", "raw")}}
        except Exception as e:                                          # noqa: BLE001  (pairgold.Skip included)
            rec = {"cell": c["cell"], "arm": c["arm"], "x1": c["x1"], "x2": c["x2"], "accepted": False,
                   "error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-1500:]}
        rec.update(seconds=round(time.time() - t0, 1), ts=_now())
        _append(run / "write.jsonl", rec)
        print("write", c["cell"], c["arm"], rec.get("accepted"), rec.get("error", "")[:100], flush=True)

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, cells))
    (run / "write.done").write_text(_now())


# ---------------------------------------------------------------------------------------------- W + V (Granite)
def wv_one(store, judge, c: dict, w: dict) -> dict:
    """Granite writes W and V guided by Luna's notes, k=K per round, up to ROUNDS rounds; the first sample that passes
    check_reply (gold structure and choice) and both Jev gates (supports the gold choice; same argument as Luna's) is
    the target, else Luna's own text. Non-random: the student prompt with the case (targets.guided_rs). Random
    (not_governed): the no-case prompt, spliced after the not_governed applicability (targets.guided_nocase; Peter
    2026-11-13: random-arm targets follow the answer key, not Granite's own choice)."""
    from pipeline.sft import targets as T
    p = T.prepare(store, c, aligned=w.get("aligner"))
    nocase = p.g.pair.relation == "not_governed"
    rec = {"cell": c["cell"], "arm": c["arm"], "x1": c["x1"], "x2": c["x2"], "relation": p.g.pair.relation,
           "choice": p.g.choice, "format": "v4"}
    rounds, chosen = [], None
    for r in range(ROUNDS):
        seed0 = 100 + K * r
        ss = (T.guided_nocase(store, p, w["text"], k=K, seed0=seed0) if nocase
              else T.guided_rs(p, w["text"], k=K, seed0=seed0, guide=True))
        for s in ss:
            if s["accepted"]:
                s["gate"] = T.gate(p, s["text"], judge, reference=w["text"])
                if chosen is None and s["gate"].get("supports") and s["gate"].get("same_argument"):
                    chosen = s
        rounds.append(ss)
        if chosen:
            break
    rec["rounds"] = rounds
    if chosen:
        rec.update(source="granite_nocase" if nocase else "granite_guided", target=chosen["text"],
                   sample=[len(rounds) - 1, chosen["i"]], target_choice=str(chosen.get("choice")), gate=chosen["gate"])
        if not nocase:
            rec["ca"] = T.case_approach_quality(p, chosen["text"], judge)
    else:
        rec.update(source="luna", target=w["text"], target_choice=p.g.choice)
        if not nocase:
            rec["ca"] = T.case_approach_quality(p, w["text"], judge)
    return rec


def wv_stage(run: Path, workers: int, follow: bool, poll: int = 60):
    from eval.core import default_judge
    from pipeline.store import Store
    store, judge = Store(), default_judge()
    cells = {c["cell"]: c for c in json.load(open(run / "cells.json"))}
    out = run / "wv.jsonl"
    done = {r["cell"] for r in _jl(out)}

    def one(w):
        t0 = time.time()
        try:
            rec = wv_one(store, judge, cells[w["cell"]], w)
        except Exception as e:                                          # noqa: BLE001
            rec = {"cell": w["cell"], "arm": w["arm"], "source": None, "error": f"{type(e).__name__}: {e}",
                   "tb": traceback.format_exc()[-1500:]}
        rec.update(seconds=round(time.time() - t0, 1), ts=_now())
        _append(out, rec)
        print("wv", rec["cell"], rec["arm"], rec.get("source"), rec.get("error", "")[:100], flush=True)

    with ThreadPoolExecutor(workers) as ex:
        while True:
            finished = (run / "write.done").exists()
            todo = [w for w in _jl(run / "write.jsonl") if w.get("accepted") and w["cell"] not in done]
            done |= {w["cell"] for w in todo}
            list(ex.map(one, todo))
            if not follow or (finished and not todo):
                break
            if not todo:
                time.sleep(poll)


# ---------------------------------------------------------------------------------------------- assemble
def assemble(run: Path) -> dict:
    from pipeline.sft import targets as T
    from pipeline.store import Store
    store = Store()
    cells = {c["cell"]: c for c in json.load(open(run / "cells.json"))}
    W = {r["cell"]: r for r in _jl(run / "write.jsonl")}
    V = {r["cell"]: r for r in _jl(run / "wv.jsonl")}
    rows = []
    for cid, v in V.items():
        if not v.get("target"):
            continue
        c, w = cells[cid], W[cid]
        p = T.prepare(store, c, aligned=w.get("aligner"))
        prompt = p.ep.generation_prompt                 # mode B: ends with the empty think block (format v4)
        target = T.drop_flips(v["target"])              # targets generated under v3 lose verdict flip_conditions
        row = {"id": f"sft-{cid}", "cell": cid, "arm": c["arm"], "x1": c["x1"], "x2": c["x2"], "chain": c["chain"],
               "relation": v["relation"], "gold_choice": v["choice"], "target_choice": v.get("target_choice"),
               "source": v["source"], "gate": v.get("gate"), "format": "v4", "mode": "B", "policy": T.GRANITE,
               "prompt": prompt, "completion": target,
               "messages": [*p.ep.messages, {"role": "assistant", "content": p.ep.opener + target}],
               "tools": p.ep.tools}
        row["sha256"] = hashlib.sha256((prompt + "\x00" + target).encode()).hexdigest()
        rows.append(row)
    with open(run / "sft.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(run / "golden.jsonl", "w") as f:        # the trainer's record format (training.sft_data)
        for r in rows:
            f.write(json.dumps({"id": r["id"], "prompt_text": r["prompt"], "completion": r["completion"], "prefill": "",
                                "meta": {"mode": r["mode"], "format": r["format"], "arm": r["arm"],
                                         "source": r["source"], "cell": r["cell"], "sha256": r["sha256"]}},
                               ensure_ascii=False) + "\n")
    rep = report(run)
    return {"rows": len(rows), "report": rep}


def report(run: Path) -> str:
    cells = json.load(open(run / "cells.json"))
    W = {r["cell"]: r for r in _jl(run / "write.jsonl")}
    V = {r["cell"]: r for r in _jl(run / "wv.jsonl")}
    by = defaultdict(Counter)
    for c in cells:
        a, w, v = c["arm"], W.get(c["cell"]), V.get(c["cell"])
        b = by[a]
        b["cells"] += 1
        b["written"] += bool(w)
        b["luna_ok"] += bool(w and w.get("accepted"))
        b["luna_error"] += bool(w and w.get("error"))
        if v:
            b["wv_done"] += 1
            b[f"src_{v.get('source')}"] += 1
            b["wv_error"] += bool(v.get("error"))
            if v.get("target_choice") is not None:
                b["choice_is_gold"] += v.get("target_choice") == v.get("choice")
    cols = ["cells", "written", "luna_ok", "luna_error", "wv_done", "src_granite_guided", "src_luna",
            "src_granite_nocase", "src_None", "wv_error", "choice_is_gold"]
    lines = ["| arm | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    tot = Counter()
    for a in ARMS:
        if a in by:
            lines.append(f"| {a} | " + " | ".join(str(by[a][k]) for k in cols) + " |")
            tot.update(by[a])
    lines.append("| **all** | " + " | ".join(str(tot[k]) for k in cols) + " |")
    md = "\n".join(lines)
    (run / "report.md").write_text(md + "\n")
    return md


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["select", "write", "wv", "assemble", "report"])
    ap.add_argument("--run", default="results/sft/gen1")
    ap.add_argument("--cells", default="data/datasets/pairs-v1/cells-full.json")
    ap.add_argument("--splits", default="train")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--follow", action="store_true", help="wv: keep picking up new writes until write.done")
    ap.add_argument("--limit", type=int, help="select: keep only the first N cells per arm (smoke test)")
    a = ap.parse_args(argv)
    run = ROOT / a.run
    if a.stage == "select":
        out = select(run, a.cells, a.splits.split(","))
        if a.limit:
            per = Counter()
            out = [c for c in out if (per.update([c["arm"]]) or per[c["arm"]] <= a.limit)]
            (run / "cells.json").write_text(json.dumps(out, indent=1))
        print(len(out), dict(Counter(c["arm"] for c in out)))
    elif a.stage == "write":
        write_stage(run, a.workers)
    elif a.stage == "wv":
        wv_stage(run, a.workers, a.follow)
    elif a.stage == "assemble":
        r = assemble(run)
        print(r["rows"], "rows\n" + r["report"])
    else:
        print(report(run))


if __name__ == "__main__":
    main()
