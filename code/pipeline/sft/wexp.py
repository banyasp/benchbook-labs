"""W experiment (Peter, 2026-11-12): how should the reasoning W (and verdict V) of an SFT target be written?

    L   Luna writes the prose from the full gold (targets.write), base Granite restates it (targets.restate);
        Jev gates: the restated W supports the gold choice, and makes the same argument as Luna's.
    G   gold-conditioned rejection sampling: base Granite gets Luna's documents through applicability as a prefill and
        writes W and V itself, k samples (targets.granite_rs); kept iff the reply passes check_reply.
    random arm: W and V from base Granite without the case (targets.nocase_wv), spliced after applicability.

    PYTHONPATH=code .venv/bin/python -m pipeline.sft.wexp sample  --run results/sft/wexp1 [--per-arm 3]
    PYTHONPATH=code .venv/bin/python -m pipeline.sft.wexp write   --run results/sft/wexp1          # Luna (Bedrock)
    PYTHONPATH=code .venv/bin/python -m pipeline.sft.wexp granite --run results/sft/wexp1 [--k 8]  # needs Granite on :8000
    PYTHONPATH=code .venv/bin/python -m pipeline.sft.wexp report  --run results/sft/wexp1
"""
from __future__ import annotations

import argparse
import json
import random
import time
import traceback
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bench.models import ROOT

ARMS = ["self", "transfer", "transfer_flip", "same_domain_flip", "noflip", "revised", "neighbor", "random"]


def _jl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def _append(path: Path, rec: dict):
    with open(path, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


def sample(run: Path, cells_file: str, per_arm: int, seed: int) -> list[dict]:
    from pipeline.store import Store
    store = Store()
    cells = json.load(open(ROOT / cells_file))
    rng = random.Random(f"wexp|{seed}")
    out, used = [], Counter()
    for arm in ARMS:
        pool = [c for c in cells if c["arm"] == arm and store.has_trace(c["x1"])]
        rng.shuffle(pool)
        pool.sort(key=lambda c: used[c["x1"]])          # spread anchors across arms
        take = []
        for c in pool:
            if len(take) == per_arm:
                break
            if any(t["x1"] == c["x1"] for t in take):
                continue
            take.append(c)
        for c in take:
            used[c["x1"]] += 1
        out += take
    run.mkdir(parents=True, exist_ok=True)
    (run / "cells.json").write_text(json.dumps(out, indent=1))
    (run / "config.json").write_text(json.dumps({"cells_file": cells_file, "per_arm": per_arm, "seed": seed,
                                                 "created": time.strftime("%FT%TZ", time.gmtime())}, indent=1))
    return out


def _prep(store, c, aligned=None):
    from pipeline.sft import targets as T
    return T.prepare(store, c, aligned=aligned)


def write_stage(run: Path, workers: int):
    from pipeline.sft import targets as T
    from pipeline.store import Store
    store = Store()
    cells = json.load(open(run / "cells.json"))
    done = {r["cell"] for r in _jl(run / "write.jsonl")}

    def one(c):
        if c["cell"] in done:
            return
        t0 = time.time()
        try:
            p = _prep(store, c)
            w = T.write(p)
            rec = {"cell": c["cell"], "arm": c["arm"], "x1": c["x1"], "x2": c["x2"], "relation": p.g.pair.relation,
                   "choice": p.g.choice, "strategy": p.built.strategy, "gold_warnings": p.g.warnings,
                   "aligner": p.built.aligner, **{k: w[k] for k in ("try", "accepted", "reasons", "flags", "text", "raw")},
                   "seconds": round(time.time() - t0, 1)}
        except Exception as e:                                          # noqa: BLE001
            rec = {"cell": c["cell"], "arm": c["arm"], "x1": c["x1"], "x2": c["x2"], "error": f"{type(e).__name__}: {e}",
                   "tb": traceback.format_exc()[-1500:]}
        _append(run / "write.jsonl", rec)
        print(c["cell"], c["arm"], rec.get("accepted"), rec.get("error", "")[:120], flush=True)

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, cells))


def granite_stage(run: Path, k: int, k_random: int, workers: int):
    from eval.core import default_judge
    from pipeline.sft import targets as T
    from pipeline.store import Store
    store = Store()
    judge = default_judge()
    cells = {c["cell"]: c for c in json.load(open(run / "cells.json"))}
    writes = {r["cell"]: r for r in _jl(run / "write.jsonl") if r.get("accepted")}
    done = {r["cell"] for r in _jl(run / "granite.jsonl")}

    def one(cid):
        if cid in done:
            return
        c, w = cells[cid], writes[cid]
        t0 = time.time()
        try:
            p = _prep(store, c, aligned=w.get("aligner"))
            rec = {"cell": cid, "arm": c["arm"], "x1": c["x1"], "x2": c["x2"], "relation": p.g.pair.relation,
                   "choice": p.g.choice}
            if p.g.pair.relation == "not_governed":                     # random arm: Peter's no-case W+V
                ss = T.nocase_wv(store, p, k=k_random)
                for s in ss:
                    if s["reasoning"] and s["verdict"]:
                        s["text"] = T.splice_random(w["text"], s["reasoning"], s["verdict"], p.g)
                        s["gate"] = T.gate(p, s["text"], judge, choice=str(s["verdict"].get("choice")))
                rec["nocase"] = ss
                ok = next((s for s in ss if s.get("text")), None)
                if ok:
                    rec["restate"] = T.restate(p, ok["text"])
            else:
                r = T.restate(p, w["text"])
                if r.get("text"):
                    r["gate"] = T.gate(p, r["text"], judge, reference=w["text"])
                rec["luna_gate"] = T.gate(p, w["text"], judge)
                rec["restate"] = r
                gs = T.granite_rs(p, w["text"], k=k)
                for s in gs:
                    if s["accepted"]:
                        s["gate"] = T.gate(p, s["text"], judge)
                rec["granite_rs"] = gs
            rec["seconds"] = round(time.time() - t0, 1)
        except Exception as e:                                          # noqa: BLE001
            rec = {"cell": cid, "arm": c["arm"], "error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()[-1500:]}
        _append(run / "granite.jsonl", rec)
        print(cid, c["arm"], rec.get("error", "ok")[:120], flush=True)

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, list(writes)))


def restate_stage(run: Path, workers: int):
    """Re-run restate + gates for every cell (after a restate change); overwrites the `restate` field in granite.jsonl
    (the old file is kept as granite.<ts>.jsonl)."""
    from eval.core import default_judge
    from pipeline.sft import targets as T
    from pipeline.store import Store
    store, judge = Store(), default_judge()
    cells = {c["cell"]: c for c in json.load(open(run / "cells.json"))}
    writes = {r["cell"]: r for r in _jl(run / "write.jsonl") if r.get("accepted")}
    G = _jl(run / "granite.jsonl")
    (run / f"granite.{int(time.time())}.jsonl").write_text("".join(json.dumps(g, ensure_ascii=False) + "\n" for g in G))

    def one(g):
        c, w = cells[g["cell"]], writes[g["cell"]]
        p = _prep(store, c, aligned=w.get("aligner"))
        if p.g.pair.relation == "not_governed":
            ok = next((s for s in g.get("nocase") or [] if s.get("text")), None)
            g["restate"] = T.restate(p, ok["text"]) if ok else None
            if g["restate"] and g["restate"].get("text"):
                ch = str((ok.get("verdict") or {}).get("choice"))
                g["restate"]["gate"] = T.gate(p, g["restate"]["text"], judge, reference=ok["text"], choice=ch)
        else:
            r = T.restate(p, w["text"])
            if r.get("text"):
                r["gate"] = T.gate(p, r["text"], judge, reference=w["text"])
            g["restate"] = r
        print(g["cell"], g["arm"], (g["restate"] or {}).get("accepted"), flush=True)
        return g

    with ThreadPoolExecutor(workers) as ex:
        G = list(ex.map(one, G))
    (run / "granite.jsonl").write_text("".join(json.dumps(g, ensure_ascii=False, default=str) + "\n" for g in G))


def report(run: Path) -> str:
    W = _jl(run / "write.jsonl")
    G = {r["cell"]: r for r in _jl(run / "granite.jsonl")}
    by = defaultdict(Counter)
    for w in W:
        a = w["arm"]
        by[a]["cells"] += 1
        by[a]["luna_ok"] += bool(w.get("accepted"))
        g = G.get(w["cell"]) or {}
        rs = g.get("granite_rs") or []
        by[a]["rs_samples"] += len(rs)
        by[a]["rs_accepted"] += sum(s["accepted"] for s in rs)
        by[a]["rs_cells_with_one"] += any(s["accepted"] for s in rs)
        by[a]["rs_choice_ok"] += sum(str(s.get("choice")) == g.get("choice") for s in rs)
        r = g.get("restate") or {}
        by[a]["restate_ok"] += bool(r.get("accepted"))
        gt = r.get("gate") or {}
        by[a]["restate_supports"] += bool(gt.get("supports"))
        by[a]["restate_same_arg"] += bool(gt.get("same_argument"))
        by[a]["luna_supports"] += bool((g.get("luna_gate") or {}).get("supports"))
        nc = g.get("nocase") or []
        by[a]["nocase_samples"] += len(nc)
        by[a]["nocase_parsed"] += sum(bool(s.get("text")) for s in nc)
        by[a]["nocase_gold_choice"] += sum(str((s.get("verdict") or {}).get("choice")) == g.get("choice") for s in nc)
    cols = ["cells", "luna_ok", "luna_supports", "restate_ok", "restate_supports", "restate_same_arg", "rs_samples",
            "rs_accepted", "rs_choice_ok", "rs_cells_with_one", "nocase_samples", "nocase_parsed", "nocase_gold_choice"]
    lines = ["| arm | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    tot = Counter()
    for a in ARMS:
        if a in by:
            lines.append(f"| {a} | " + " | ".join(str(by[a][c]) for c in cols) + " |")
            tot.update(by[a])
    lines.append("| **all** | " + " | ".join(str(tot[c]) for c in cols) + " |")
    md = "\n".join(lines)
    (run / "report.md").write_text(md + "\n")
    return md


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["sample", "write", "granite", "restate", "likelihood", "guided", "report"])
    ap.add_argument("--run", default="results/sft/wexp1")
    ap.add_argument("--cells", default="data/datasets/pairs-v1/cells-pilot.json")
    ap.add_argument("--per-arm", type=int, default=3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--k-random", type=int, default=4)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--guide", action="store_true", help="guided: add the case_approach guidance to the prompt")
    ap.add_argument("--out", help="guided: output file name in the run dir")
    a = ap.parse_args(argv)
    run = ROOT / a.run
    if a.stage == "sample":
        out = sample(run, a.cells, a.per_arm, a.seed)
        print(Counter(c["arm"] for c in out))
    elif a.stage == "write":
        write_stage(run, a.workers)
    elif a.stage == "guided":
        guided_stage(run, a.k, a.workers, guide=a.guide, out_name=a.out or "guided.jsonl")
    elif a.stage == "likelihood":
        import statistics as st
        res = likelihood_stage(run, a.workers)
        for k in ("luna", "restated", "granite"):
            v = [r[k]["mean_logprob"] for r in res if r.get(k)]
            print(k, "n", len(v), "median mean-logprob/token", round(st.median(v), 3) if v else None)
    elif a.stage == "restate":
        restate_stage(run, a.workers)
    elif a.stage == "granite":
        granite_stage(run, a.k, a.k_random, a.workers)
    else:
        print(report(run))



# ---------------------------------------------------------------------------------------------- likelihood under base Granite
def w_logprob(p, target: str) -> dict:
    """Mean log-probability per token of the reasoning document (W) of `target` under base Granite, given the student
    prompt (mode B) and the target's own documents before W. A forward pass (vLLM prompt_logprobs), no sampling.
    Proxy for how far a target sits from Granite's own distribution (Peter's KL argument for restating)."""
    import requests
    from harness.episode import tokenizer
    i = target.find("kind: reasoning")
    j = target.find("\n---\nkind: verdict", i)
    if i < 0 or j < 0:
        return {}
    tok = tokenizer(p.settings.tokenizer)
    pre = p.ep.prompt_text + target[:i]
    full = pre + target[i:j]
    n0, n1 = len(tok(pre, add_special_tokens=False)["input_ids"]), len(tok(full, add_special_tokens=False)["input_ids"])
    r = requests.post("http://localhost:8000/v1/completions", timeout=600, json={
        "model": GRANITE_NAME, "prompt": full, "max_tokens": 1, "temperature": 0, "prompt_logprobs": 0,
        "add_special_tokens": False}).json()
    pl = r["choices"][0]["prompt_logprobs"]
    lps = []
    for d in pl[n0:n1]:
        if d:
            lps.append(max(v["logprob"] for v in d.values()) if len(d) == 1 else next(iter(d.values()))["logprob"])
    return {"tokens": len(lps), "mean_logprob": round(sum(lps) / max(1, len(lps)), 4)}


GRANITE_NAME = "granite-4.2-8b"


def likelihood_stage(run: Path, workers: int):
    from pipeline.sft import targets as T
    from pipeline.store import Store
    store = Store()
    cells = {c["cell"]: c for c in json.load(open(run / "cells.json"))}
    writes = {r["cell"]: r for r in _jl(run / "write.jsonl") if r.get("accepted")}
    G = [g for g in _jl(run / "granite.jsonl") if g["arm"] != "random"]

    def one(g):
        c, w = cells[g["cell"]], writes[g["cell"]]
        p = _prep(store, c, aligned=w.get("aligner"))
        out = {"cell": g["cell"], "arm": g["arm"], "luna": w_logprob(p, w["text"]),
               "restated": w_logprob(p, (g.get("restate") or {}).get("text") or "")}
        acc = [s for s in g.get("granite_rs") or [] if s["accepted"]]
        if acc:
            out["granite"] = w_logprob(p, acc[0]["text"])
        return out

    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(one, G))
    (run / "likelihood.json").write_text(json.dumps(res, indent=1))
    return res

def guided_stage(run: Path, k: int, workers: int, guide: bool = False, out_name: str = "guided.jsonl"):
    """Granite writes W+V with the writer's reasoning as notes in the prompt; gates + likelihood per accepted sample."""
    from eval.core import default_judge
    from pipeline.sft import targets as T
    from pipeline.store import Store
    store, judge = Store(), default_judge()
    cells = {c["cell"]: c for c in json.load(open(run / "cells.json"))}
    writes = {r["cell"]: r for r in _jl(run / "write.jsonl") if r.get("accepted") and r["arm"] != "random"}

    def one(cid):
        c, w = cells[cid], writes[cid]
        p = _prep(store, c, aligned=w.get("aligner"))
        ss = T.guided_rs(p, w["text"], k=k, guide=guide)
        for s in ss:
            if s["accepted"]:
                s["gate"] = T.gate(p, s["text"], judge, reference=w["text"])
                s["lik"] = w_logprob(p, s["text"])
                s["ca"] = T.case_approach_quality(p, s["text"], judge)
        print(cid, c["arm"], [s["accepted"] for s in ss], flush=True)
        return {"cell": cid, "arm": c["arm"], "choice": p.g.choice, "guided": ss}

    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(one, list(writes)))
    with open(run / out_name, "w") as f:
        for r in res:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    return res


if __name__ == "__main__":
    main()
