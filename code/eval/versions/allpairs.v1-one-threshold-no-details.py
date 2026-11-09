"""All-pairs case-benefit experiment (Peter, 2026-11-09; whiteboard IMG_4398-4400 in docs/figures/).

For every live scenario X1 (needs a rendered trace T(X1)) and every library scenario X2 (served as the case C(X2)):

    case    G(T(X1), C(X2))   base Granite, mode C, AR prompt on, full card, equities E_d (default pilot2)
    control G(T(X1))          same, no case (the `-noref` format: no mapping steps), k samples per X1

Every reply is scored against X1's own answer key (F, Q, K, V from extraction), never against a pair gold: the verdict
is translated to X1's options by Jev Choice and exact-matched (primary objective); facts / frame / options /
considerations enumeration scores are kept as secondary metrics. W (reasoning) is stored, not scored.

Phases (one samples.jsonl, resumable; a sample is skipped if its id is already there):
    grid     one sample per (X1, X2), X2 = X1 included (the self cell), scheduled in ROUNDS (round r = the r-th X2 of
             every X1 in a seeded per-X1 order) so a partial run is a balanced partial grid; the k control samples
             are spread over the run.
    confirm  for each X1, one X2 != X1 drawn at random (seeded) from those whose grid sample was correct, re-run k times
             (fresh sampling seeds). Its success rate is X1's "best case" score; an X1 with no successful X2 scores 0.
             This removes the pass@N inflation of "any X2 succeeds" (see the report).

    PYTHONPATH=code .venv/bin/python -m eval.allpairs run --x1 <ids.txt> [--x2 <ids.txt>] --run results/allpairs/A1
    PYTHONPATH=code .venv/bin/python -m eval.allpairs confirm --run results/allpairs/A1
    PYTHONPATH=code .venv/bin/python -m eval.allpairs_report --run results/allpairs/A1

Sampling seed: vLLM samples each token at temperature > 0 with a random-number generator; `seed` fixes that generator
so a sample can be reproduced. It is not a property of the model. Each sample gets its own seed (hash of run seed and
sample id).
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import random
import sys
import time
from pathlib import Path

from bench.schema import parse_reply

from .core import read_samples, safe_name, usage_tokens

MODELS = {"base": "granite-4.2-8b", "sft": "sft"}
MODE = "C"
SECONDARY = ("facts_enum", "facts_enum.found", "facts_enum.n_gold", "options_enum", "options_enum.found",
             "options_enum.n_gold", "frame_question", "frame_decider", "frame_role", "considerations_enum",
             "considerations_enum.found", "considerations_enum.n_gold", "considerations_enum.equity",
             "schema_valid", "options_correct_omitted")


# ------------------------------------------------------------------ X1 / X2 setup
def lineage_root(sc) -> str:
    return sc.family


def none_pair(store, x1: str, equities: str):
    """A synthetic arm-`none` PairRecord for X1: its gold is X1's own answer key (F, Q, K, V)."""
    from bench.schema.pipeline import FrameCmp, GoldMap, PairRecord
    T = store.scenario(x1)
    tr = store.trace(x1)
    c = T.case
    return PairRecord(
        id=f"AP-{hashlib.sha256(x1.encode()).hexdigest()[:10]}", intent="none", arm="none", card_view="full",
        ar_prompt=True, case_scenario="", trace_scenario=x1, split="test", equities=equities,   # eval-only pair (arm none); X1's split is kept as x1_split
        frame=FrameCmp(question="different", decider="different", role="different"),
        options_map={c.global_id(o): None for o in c.options},
        fact_map=GoldMap(matched=[], corresponding=[], live_only=[c.global_id(f.id) for f in c.facts], case_only=[]),
        consideration_map=GoldMap(matched=[], corresponding=[], live_only=[c.global_id(k.id) for k in c.considerations],
                                  case_only=[]),
        governs=False, relation="not_governed", choice=c.global_id(c.verdict.choice), acceptable=[],
        gold_tier=T.verdict_tier, recommended_option=tr.recommended_option, trace_ref=x1, tags=["allpairs"])


def case_pair(base, x2: str):
    """The same X1 pair with C(X2) served. Only prompt building reads it (arm != none -> a card)."""
    return base.model_copy(update={"arm": "relevant", "case_scenario": x2})


def relation_tag(store, x1: str, x2: str) -> str:
    """self | derived (one is a perturbation of the other, or siblings of one parent) | same_family | other."""
    if x1 == x2:
        return "self"
    a, b = store.scenario(x1), store.scenario(x2)
    pa = (a.lineage.parent if getattr(a, "lineage", None) else None) or x1
    pb = (b.lineage.parent if getattr(b, "lineage", None) else None) or x2
    if pa == x2 or pb == x1 or pa == pb:
        return "derived"
    if a.family == b.family:
        return "same_family"
    return "other"


# ------------------------------------------------------------------ schedule
def sample_seed(run_seed: int, sid: str) -> int:
    return int(hashlib.sha256(f"{run_seed}|{sid}".encode()).hexdigest()[:8], 16) % (2**31 - 1)


def grid_schedule(x1s: list[str], x2s: list[str], k_control: int, run_seed: int) -> list[dict]:
    """Items in run order: control idx 0 and self cells first, then rounds; control idx j after round j*R/k."""
    order = {}
    for x1 in x1s:
        rest = [x for x in x2s if x != x1]
        random.Random(f"{run_seed}|order|{x1}").shuffle(rest)
        order[x1] = rest
    items = [{"phase": "control", "x1": x1, "x2": None, "idx": 0} for x1 in x1s]
    items += [{"phase": "grid", "x1": x1, "x2": x1, "idx": 0} for x1 in x1s if x1 in x2s]
    R = max(len(v) for v in order.values()) if order else 0
    every = max(1, R // max(1, k_control))
    j = 1
    for r in range(R):
        items += [{"phase": "grid", "x1": x1, "x2": order[x1][r], "idx": 0} for x1 in x1s if r < len(order[x1])]
        if (r + 1) % every == 0 and j < k_control:
            items += [{"phase": "control", "x1": x1, "x2": None, "idx": j} for x1 in x1s]
            j += 1
    while j < k_control:
        items += [{"phase": "control", "x1": x1, "x2": None, "idx": j} for x1 in x1s]
        j += 1
    return items


def sid_of(it: dict, model: str) -> str:
    return f"{model}|{it['phase']}|{it['x1']}|{it['x2'] or '-'}|{it['idx']}"


def confirm_schedule(samples: list[dict], k: int, run_seed: int, model: str) -> tuple[list[dict], dict]:
    """-> (items, picks). picks[x1] = chosen X2 (or None: no X2 != X1 succeeded in the grid)."""
    ok: dict[str, list[str]] = {}
    x1s = set()
    for r in samples:
        if r["model"] != model or r["phase"] != "grid":
            continue
        x1s.add(r["x1"])
        if r["x2"] != r["x1"] and r.get("correct") == 1.0:
            ok.setdefault(r["x1"], []).append(r["x2"])
    picks, items = {}, []
    for x1 in sorted(x1s):
        c = sorted(ok.get(x1, []))
        picks[x1] = random.Random(f"{run_seed}|pick|{x1}").choice(c) if c else None
        if picks[x1]:
            items += [{"phase": "confirm", "x1": x1, "x2": picks[x1], "idx": i} for i in range(1, k + 1)]
    return items, picks


# ------------------------------------------------------------------ one sample
class Ctx:
    def __init__(self, store, run_dir: Path, model: str, equities: str, judge, run_seed: int, max_tokens: int,
                 concurrency: int):
        import harness
        from harness.pairs import build_pair_episode
        from .core import score_reply_with_details
        self.store, self.run_dir, self.model, self.equities, self.judge = store, run_dir, model, equities, judge
        self.run_seed, self.max_tokens = run_seed, max_tokens
        self.sem, self.lock = asyncio.Semaphore(concurrency), asyncio.Lock()
        self.arun, self.Settings, self.build, self.score = (harness.arun_episode, harness.HarnessSettings,
                                                            build_pair_episode, score_reply_with_details)
        self._pairs, self._keys, self._meta, self._rel = {}, {}, {}, {}

    def pair_and_key(self, x1: str):
        if x1 not in self._pairs:
            from pipeline.project.project import gold_for
            p = none_pair(self.store, x1, self.equities)
            g, key = gold_for(p, self.store)
            T = self.store.scenario(x1)
            self._pairs[x1], self._keys[x1] = p, key
            self._meta[x1] = {"family": T.family, "domain": T.domain, "content_domain": getattr(T, "content_domain", None),
                              "held_out": bool(T.held_out), "split": T.split, "n_options": len(g.option_ids),
                              "gold_position": g.option_ids.index(g.choice) + 1, "warnings": g.warnings}
        return self._pairs[x1], self._keys[x1], self._meta[x1]

    def rel(self, x1, x2):
        if x2 is None:
            return None
        if (x1, x2) not in self._rel:
            self._rel[(x1, x2)] = relation_tag(self.store, x1, x2)
        return self._rel[(x1, x2)]


async def run_one(ctx: Ctx, it: dict, done: set) -> dict | None:
    sid = sid_of(it, ctx.model)
    if sid in done:
        return None
    try:
        base, key, meta = ctx.pair_and_key(it["x1"])
        pair = base if it["x2"] is None else case_pair(base, it["x2"])
        seed = sample_seed(ctx.run_seed, sid)
        settings = ctx.Settings(mode=MODE, analogical_prompt=True, max_tokens=ctx.max_tokens, seed=seed,
                                model=MODELS[ctx.model])
        ep = await asyncio.to_thread(ctx.build, pair, ctx.store, settings)
        async with ctx.sem:
            out = await ctx.arun(ep, settings)
        raw = out.raw_text
        parsed = parse_reply(raw, noref=it["x2"] is None)
        scores, err = None, None
        try:   # scored against X1's key only: served=None, so no mapping gold is consulted
            scores = await asyncio.to_thread(ctx.score, parsed, key, None, ctx.judge)
        except Exception as e:                                   # noqa: BLE001  judge down: keep, rescore later
            err = f"{type(e).__name__}: {e}"
        rel = f"raw/{safe_name(sid)}.txt"
        (ctx.run_dir / rel).write_text(raw)
        verdict = parsed.steps.get("verdict", {}) or {}
        s = scores or {}
        choice = verdict.get("choice")
        tc = s.get("translated_choice")
        cu = s.get("verdict_choice_ungated")
        rec = {"sample_id": sid, "model": ctx.model, **it, "relation_x1_x2": ctx.rel(it["x1"], it["x2"]),
               "x2_family": ctx.store.scenario(it["x2"]).family if it["x2"] else None,
               **{f"x1_{k}": v for k, v in meta.items() if k != "warnings"},
               "seed": seed, "parsed_choice": choice, "translated_choice": tc, "gold_choice": key.choice,
               "correct": 0.0 if choice is None else (None if cu is None else float(cu)),
               "off_menu": bool(choice is not None and tc is None),
               "model_relation": verdict.get("relation"),
               "secondary": {k: s.get(k) for k in SECONDARY}, "score_error": err,
               "tokens": usage_tokens(out, raw), "seconds": getattr(out, "seconds", None),
               "finish_reason": getattr(out, "finish_reason", None),
               "format_repairs": list(getattr(parsed, "repairs", []) or [])[:10], "raw_path": rel, "ts": time.time()}
        async with ctx.lock:
            with open(ctx.run_dir / "samples.jsonl", "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        done.add(sid)
        return rec
    except Exception as e:                                       # noqa: BLE001
        with open(ctx.run_dir / "errors.jsonl", "a") as f:
            f.write(json.dumps({"sample_id": sid, "error": f"{type(e).__name__}: {e}"[:500], "ts": time.time()}) + "\n")
        return None


async def run_items(ctx: Ctx, items: list[dict], progress_every: int = 50) -> dict:
    sp = ctx.run_dir / "samples.jsonl"
    done = {r["sample_id"] for r in read_samples(sp)} if sp.exists() else set()
    todo = [it for it in items if sid_of(it, ctx.model) not in done]
    t0, k = time.time(), 0
    # bounded window of tasks so the schedule order is kept (rounds) and memory stays flat
    window = 4 * ctx.sem._value if hasattr(ctx.sem, "_value") else 96
    pending: set = set()
    it_iter = iter(todo)
    for it in it_iter:
        pending.add(asyncio.create_task(run_one(ctx, it, done)))
        if len(pending) >= window:
            fin, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            k += len(fin)
            if progress_every and k // progress_every != (k - len(fin)) // progress_every:
                print(f"{k}/{len(todo)} done, {time.time() - t0:.0f}s", file=sys.stderr, flush=True)
    if pending:
        await asyncio.wait(pending)
        k += len(pending)
    errs = ctx.run_dir / "errors.jsonl"
    return {"ran": len(todo), "skipped_done": len(items) - len(todo), "seconds": round(time.time() - t0, 1),
            "errors_total": sum(1 for _ in errs.open()) if errs.exists() else 0}


def read_ids(path: str) -> list[str]:
    return [l.strip() for l in Path(path).read_text().splitlines() if l.strip() and not l.startswith("#")]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", choices=["run", "confirm"])
    ap.add_argument("--run", required=True)
    ap.add_argument("--x1", help="file of X1 scenario ids (need traces); stored in the run dir on first use")
    ap.add_argument("--x2", help="file of X2 scenario ids (default: the X1 list)")
    ap.add_argument("--model", default="base", choices=list(MODELS))
    ap.add_argument("--equities", default="pilot2")
    ap.add_argument("-k", type=int, default=8, help="control samples per X1; confirm re-runs per X1")
    ap.add_argument("--concurrency", type=int, default=24)
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--judge", default="jev", choices=["jev", "stub"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, help="first N scheduled items only (smoke test)")
    a = ap.parse_args(argv)
    from pipeline.store import Store
    from .core import default_judge
    run_dir = Path(a.run)
    (run_dir / "raw").mkdir(parents=True, exist_ok=True)
    cfg_p = run_dir / "config.json"
    if cfg_p.exists():
        cfg = json.loads(cfg_p.read_text())
    else:
        if not a.x1:
            raise SystemExit("--x1 is required on the first run")
        x1s = read_ids(a.x1)
        cfg = {"x1": x1s, "x2": read_ids(a.x2) if a.x2 else x1s, "model": a.model, "equities": a.equities,
               "k": a.k, "max_tokens": a.max_tokens, "seed": a.seed, "mode": MODE, "ar_prompt": True,
               "card_view": "full", "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
        cfg_p.write_text(json.dumps(cfg, indent=1))
    store = Store()
    ctx = Ctx(store, run_dir, cfg["model"], cfg["equities"], default_judge(a.judge), cfg["seed"], cfg["max_tokens"],
              a.concurrency)
    if a.phase == "run":
        items = grid_schedule(cfg["x1"], cfg["x2"], cfg["k"], cfg["seed"])
    else:
        items, picks = confirm_schedule(list(read_samples(run_dir / "samples.jsonl")), cfg["k"], cfg["seed"], cfg["model"])
        (run_dir / f"confirm-picks.{time.strftime('%Y%m%dT%H%M%S')}.json").write_text(json.dumps(picks, indent=1))
    if a.limit:
        items = items[:a.limit]
    m = asyncio.run(run_items(ctx, items))
    m.update(phase=a.phase, scheduled=len(items), ts=time.strftime("%Y-%m-%dT%H:%M:%S"))
    (run_dir / f"manifest.{a.phase}.{time.strftime('%Y%m%dT%H%M%S')}.json").write_text(json.dumps(m, indent=1))
    print(json.dumps(m, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
