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
from typing import Any

from bench.schema import parse_reply

from .core import read_samples, safe_name, usage_tokens

MODELS = {"base": "granite-4.2-8b", "sft": "sft", "luna": "bedrock/us.openai.gpt-6-luna"}
# Comparison policies called through a chat API instead of the local vLLM raw-completions harness (2026-11-09, Peter:
# is the no-case weakness specific to the 8B model?). Same episode messages (system prompt + flattened trace with the
# injection), same scorer. Differences, recorded in config.json: no assistant prefill (an instruction to begin with
# the first document stands in for it), the model's own hidden reasoning runs before the reply, and GPT-6 on Bedrock
# takes no temperature (provider default sampling).
API_ROLES = {"luna": "policy_luna"}
API_START = ("\n\nYour reply is the written decision record in the YAML documents specified above (they are a record for "
             "the deployer, not your private chain of thought, which stays hidden). Begin your reply with the line "
             "`kind: fact_enumeration` (the first YAML document), with nothing before it.")
MODE = "C"
# Scaffold ablation (Peter, 2026-11-10): how much of the result comes from decomposing the reasoning into steps
# (guidance) and how much from imposing the YAML schema on those steps? Every scaffold ends with a structured verdict
# block so the choice can be scored the same way.
#   schema: the YAML step documents (format.v1*, + analogical.v1 with a case)        -- the pilots so far
#   guided: the same steps as prose guidance, no format; analogical.v1 kept with a case; verdict block at the end
#   free:   no step guidance and no method prompt; "decide", verdict block at the end
SCAFFOLDS = {"schema": dict(format_spec="v1", modes_version="v1", analogical=True),
             "guided": dict(format_spec="v2guided", modes_version="v2", analogical=True),
             "free": dict(format_spec="v2free", modes_version="v2", analogical=False)}
API_START_PROSE = ("\n\nYour reply is the written decision record specified above, for the deployer (your private chain "
                   "of thought stays hidden). End it with the verdict block exactly as specified.")
SECONDARY = ("facts_enum", "facts_enum.found", "facts_enum.n_gold", "options_enum", "options_enum.found",
             "options_enum.n_gold", "frame_question", "frame_decider", "frame_role", "considerations_enum",
             "considerations_enum.found", "considerations_enum.n_gold", "considerations_enum.equity",
             "schema_valid", "options_correct_omitted")


# Scoring settings (2026-11-09): options -- the verdict translation -- use the tuned option instruction (judge prompts
# v2) and match above 0.5 (Peter started at 0.7; hand-labelled tuning showed 0.7 lost half the real matches); facts and
# considerations keep 0.5; ENUM / SET_COMPARE weights are the alignment.py defaults (secondary metrics only).
# Every sample keeps ALL score rows and the full judge output (alignment matrices R, C, S per step: Jev Choice
# probabilities) in details/<sample>.json, so thresholds and weights can be changed later and re-applied with
# `rescore` (the judge cache makes that free) without generating again.
SCORING = {"version": "allpairs-scoring-v3", "threshold": 0.5, "option_threshold": 0.5, "judge_prompts": "v2 (option instruction tuned 2026-11-09)",
           "weights": "alignment.py defaults"}   # v2 had option_threshold 0.7 with judge prompts v1


def score_full(parsed, key, judge) -> tuple[dict, dict]:
    from scorers import score_reply_detailed
    r = score_reply_detailed(parsed, key, None, judge, threshold=SCORING["threshold"],
                             option_threshold=SCORING["option_threshold"])
    rows = dict(r.rows)
    rows["translated_choice"] = ((r.details.get("notes") or {}).get("choice") or {}).get("gold_id")
    om = rows.get("options_correct_omitted")
    rows["gold_option_present"] = None if om is None else 1 - om
    return rows, r.details


def score_fields(parsed, key, rows: dict | None, err: str | None) -> dict:
    verdict = parsed.steps.get("verdict", {}) or {}
    s = rows or {}
    choice = verdict.get("choice")
    tc = s.get("translated_choice")
    cu = s.get("verdict_choice_ungated")
    return {"parsed_choice": choice, "translated_choice": tc, "gold_choice": key.choice,
            "correct": 0.0 if choice is None else (None if cu is None else float(cu)),
            "off_menu": bool(choice is not None and tc is None), "model_relation": verdict.get("relation"),
            "secondary": {k: s.get(k) for k in SECONDARY}, "scores": rows, "score_error": err,
            "scoring": SCORING}


def write_details(run_dir: Path, sid: str, details: dict | None) -> str | None:
    if details is None:
        return None
    rel = f"details/{safe_name(sid)}.json"
    (run_dir / "details").mkdir(exist_ok=True)
    (run_dir / rel).write_text(json.dumps(details, ensure_ascii=False, default=str))
    return rel


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


def pairs_schedule(cells: list[dict], k: int) -> list[dict]:
    """Explicit cells (transfer pilot): control k per X1, then k samples of each {x1, x2, arm}; the arm is the phase.
    Ordered sample-major (all cells' sample 0, then sample 1, ...) so a partial run covers every cell."""
    x1s = list(dict.fromkeys(c["x1"] for c in cells))
    items = []
    for i in range(k):
        items += [{"phase": "control", "x1": x, "x2": None, "idx": i} for x in x1s]
        items += [{"phase": c["arm"], "x1": c["x1"], "x2": c["x2"], "idx": i} for c in cells]
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
        self.mode = MODE
        self.scaffold = "schema"
        self.modes_version = None
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


def git_state() -> dict:
    """Commit and dirty files at launch (2026-11-11, Peter: each run page shows what changed since the last run)."""
    import subprocess
    def g(*args):
        try:
            return subprocess.run(["git", *args], capture_output=True, text=True, timeout=20,
                                  cwd=Path(__file__).resolve().parents[2]).stdout.strip()
        except Exception:                                             # noqa: BLE001
            return None
    dirty = g("status", "--porcelain", "--", "code", "config")
    return {"commit": g("rev-parse", "HEAD"), "dirty_code": dirty.splitlines() if dirty else []}


def api_generate(ep, role: str, max_tokens: int, start: str = API_START):
    """One reply from an API policy (bench.models.complete; provenance and cost are logged there)."""
    from types import SimpleNamespace
    from bench.models import complete
    msgs = [dict(m) for m in ep.messages]
    msgs[-1]["content"] = msgs[-1]["content"].rstrip() + start
    t0 = time.time()
    text = complete(role, msgs, stage="allpairs-policy", max_tokens=max_tokens) or ""
    return SimpleNamespace(raw_text=text, content=text, reasoning=None, usage=None, finish_reason=None,
                           seconds=round(time.time() - t0, 2))


async def run_one(ctx: Ctx, it: dict, done: set) -> dict | None:
    sid = sid_of(it, ctx.model)
    if sid in done:
        return None
    try:
        base, key, meta = ctx.pair_and_key(it["x1"])
        pair = base if it["x2"] is None else case_pair(base, it["x2"])
        seed = sample_seed(ctx.run_seed, sid)
        sc = SCAFFOLDS[ctx.scaffold]
        settings = ctx.Settings(mode=ctx.mode, analogical_prompt=sc["analogical"], max_tokens=ctx.max_tokens, seed=seed,
                                model=MODELS[ctx.model], format_spec=sc["format_spec"], modes_version=ctx.modes_version or sc["modes_version"])
        ep = await asyncio.to_thread(ctx.build, pair, ctx.store, settings, ar_prompt=sc["analogical"])   # the pair says True
        async with ctx.sem:
            if ctx.model in API_ROLES:
                out = await asyncio.to_thread(api_generate, ep, API_ROLES[ctx.model], ctx.max_tokens,
                                              API_START if ctx.scaffold == "schema" else API_START_PROSE)
            else:
                out = await ctx.arun(ep, settings)
        raw = out.raw_text
        parsed = parse_reply(raw, noref=it["x2"] is None)
        rows, details, err = None, None, None
        try:   # scored against X1's key only: served=None, so no mapping gold is consulted
            rows, details = await asyncio.to_thread(score_full, parsed, key, ctx.judge)
        except Exception as e:                                   # noqa: BLE001  judge down: keep, rescore later
            err = f"{type(e).__name__}: {e}"
        rel = f"raw/{safe_name(sid)}.txt"
        (ctx.run_dir / rel).write_text(raw)
        rec = {"sample_id": sid, "model": ctx.model, **it, "relation_x1_x2": ctx.rel(it["x1"], it["x2"]),
               "x2_family": ctx.store.scenario(it["x2"]).family if it["x2"] else None,
               **{f"x1_{k}": v for k, v in meta.items() if k != "warnings"},
               "seed": seed, **score_fields(parsed, key, rows, err),
               "details_path": write_details(ctx.run_dir, sid, details),
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


def rescore_run(run_dir: Path, store, judge, workers: int = 16) -> dict:
    """Re-parse every saved raw reply and re-score it with the current SCORING (judge answers come from the cache when
    unchanged). Generation fields (tokens, seconds, seed, ...) are kept. samples.jsonl is copied to versions/ first."""
    import shutil
    from collections import Counter
    from concurrent.futures import ThreadPoolExecutor
    sp = run_dir / "samples.jsonl"
    old = [json.loads(l) for l in sp.read_text().splitlines() if l.strip()]
    keys: dict[str, Any] = {}

    def key_of(x1):
        if x1 not in keys:
            from pipeline.project.project import gold_for
            keys[x1] = gold_for(none_pair(store, x1, "pilot2"), store)[1]
        return keys[x1]

    for x1 in {r["x1"] for r in old}:
        key_of(x1)

    def one(r):
        rp = run_dir / r["raw_path"]
        if not rp.exists():
            return r, "kept (no raw)"
        parsed = parse_reply(rp.read_text(), noref=r["x2"] is None)
        key = keys[r["x1"]]
        rows, details, err = None, None, None
        try:
            rows, details = score_full(parsed, key, judge)
        except Exception as e:                                   # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
        new = {**r, **score_fields(parsed, key, rows, err), "details_path": write_details(run_dir, r["sample_id"], details),
               "rescored": time.time()}
        return new, "rescored" if err is None else "score error"

    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(one, old))
    (run_dir / "versions").mkdir(exist_ok=True)
    shutil.copy2(sp, run_dir / "versions" / f"samples.{time.strftime('%Y%m%dT%H%M%S')}-before-rescore.jsonl")
    sp.write_text("".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r, _ in res))
    flips = sum(1 for (r, _), o in zip(res, old) if r.get("correct") != o.get("correct"))
    return {**dict(Counter(st for _, st in res)), "correct_changed": flips, "scoring": SCORING}


def read_ids(path: str) -> list[str]:
    return [l.strip() for l in Path(path).read_text().splitlines() if l.strip() and not l.startswith("#")]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", choices=["run", "confirm", "rescore"])
    ap.add_argument("--run", required=True)
    ap.add_argument("--x1", help="file of X1 scenario ids (need traces); stored in the run dir on first use")
    ap.add_argument("--x2", help="file of X2 scenario ids (default: the X1 list)")
    ap.add_argument("--model", default="base", choices=list(MODELS))
    ap.add_argument("--mode", default=MODE, choices=["A", "C"],
                    help="C: the structured reply is the thinking (prefilled); A: free thinking first, then the reply "
                         "(2026-11-10 ablation: does Granite copy because the format leaves no room to reason?)")
    ap.add_argument("--scaffold", default="schema", choices=list(SCAFFOLDS),
                    help="schema: YAML step documents; guided: the steps as prose guidance; free: no steps. All end "
                         "with a verdict block (2026-11-10 ablation). guided/free need --mode A for Granite")
    ap.add_argument("--modes-version", choices=["v1", "v2"],
                    help="mode-line file (code/harness/prompts/modes.<v>.yaml); default: the scaffold's own (schema v1, "
                         "guided/free v2). 2026-11-11: schema with v2 removes the v1 wording difference from the ablation")
    ap.add_argument("--equities", default="pilot2")
    ap.add_argument("-k", type=int, default=8, help="control samples per X1; confirm re-runs per X1")
    ap.add_argument("--concurrency", type=int, default=24)
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--judge", default="jev", choices=["jev", "stub"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--limit", type=int, help="first N scheduled items only (smoke test)")
    ap.add_argument("--cells", help="JSON list of {x1, x2, arm}: explicit cells instead of the full grid (transfer pilot)")
    a = ap.parse_args(argv)
    from pipeline.store import Store
    from .core import default_judge
    run_dir = Path(a.run)
    (run_dir / "raw").mkdir(parents=True, exist_ok=True)
    cfg_p = run_dir / "config.json"
    if cfg_p.exists():
        cfg = json.loads(cfg_p.read_text())
    else:
        if not a.x1 and not a.cells:
            raise SystemExit("--x1 or --cells is required on the first run")
        x1s = read_ids(a.x1) if a.x1 else []
        cells = json.loads(Path(a.cells).read_text()) if a.cells else None
        if cells:
            x1s = list(dict.fromkeys(c["x1"] for c in cells))
        cfg = {"x1": x1s, "x2": (sorted({c["x2"] for c in cells}) if cells else (read_ids(a.x2) if a.x2 else x1s)),
               "cells": cells, "model": a.model, "equities": a.equities,
               "k": a.k, "max_tokens": a.max_tokens, "seed": a.seed, "mode": a.mode, "scaffold": a.scaffold,
               "ar_prompt": SCAFFOLDS[a.scaffold]["analogical"], "format_spec": SCAFFOLDS[a.scaffold]["format_spec"],
               "modes_version": a.modes_version or SCAFFOLDS[a.scaffold]["modes_version"],
               "card_view": "full", "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "git": git_state(),
               **({"api_role": API_ROLES[a.model],
                   "api_start_instruction": API_START if a.scaffold == "schema" else API_START_PROSE, "prefill": None,
                   "temperature": "provider default (GPT-6 on Bedrock takes none)"} if a.model in API_ROLES else {})}
        cfg_p.write_text(json.dumps(cfg, indent=1))
    store = Store()
    ctx = Ctx(store, run_dir, cfg["model"], cfg["equities"], default_judge(a.judge), cfg["seed"], cfg["max_tokens"],
              a.concurrency)
    ctx.mode = cfg.get("mode") or MODE
    ctx.scaffold = cfg.get("scaffold") or "schema"
    ctx.modes_version = cfg.get("modes_version")
    if ctx.modes_version == "v2" and ctx.mode not in ("A", "B"):
        raise SystemExit("modes.v2 defines only A and B (no structure inside <think>): use --mode A")
    if ctx.scaffold != "schema" and ctx.model not in API_ROLES and ctx.mode != "A":
        raise SystemExit("--scaffold guided/free has no structure to put inside <think>: use --mode A for Granite")
    if a.phase == "rescore":
        print(json.dumps(rescore_run(run_dir, store, ctx.judge), indent=1))
        return 0
    if a.phase == "run":
        items = (pairs_schedule(cfg["cells"], cfg["k"]) if cfg.get("cells")
                 else grid_schedule(cfg["x1"], cfg["x2"], cfg["k"], cfg["seed"]))
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
