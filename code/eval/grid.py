"""Core grid runner (design §13.1): {base, SFT} x {none, relevant, augmented, revised, decoy, self}, AR prompt on, full card,
n = 1, mode C. Built from the v1 eval export (`python -m pipeline.project --version v1 --mode C`), run against the vLLM
server (model `granite-4.2-8b` = base, `sft` = the LoRA adapter, see inference/serve.sh), many requests in flight,
resumable (samples already in samples.jsonl are skipped).

    PYTHONPATH=code .venv/bin/python -m eval.grid --export data/exports/v1/eval/inspect.jsonl \\
        --run results/eval-v1/run1 --models base sft --concurrency 24 [--judge jev|stub]

Second-pass cells are wired, not part of the default run: `--cells core ar_off thin eq_off` (AR prompt off; thin card
view on eligible relevant pairs; equities E_d off with card none / relevant). Nothing runs them unless asked.

samples.jsonl: one flat record per (model, export row, sample idx); `eval.grid_report` reads it.

After a parser or scorer change, re-parse and re-score the saved raw replies without generating (the old samples.jsonl is
copied to <run>/versions/ first; the judge cache makes unchanged calls free):

    PYTHONPATH=code .venv/bin/python -m eval.grid --run results/eval-v1/run1 --rescore
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import shutil
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from bench.schema import AnswerKey, parse_reply

from . import score_names
from .core import format_report, gold_cues, read_samples, safe_name, usage_tokens

MODELS = {"base": "granite-4.2-8b", "sft": "sft"}          # label -> vLLM served model name
GRID_ARMS = ("none", "relevant", "augmented", "revised", "decoy", "self")
CELLS = ("core", "ar_off", "thin", "eq_off")
MODE = "C"


# ------------------------------------------------------------------ export rows
def load_export(path, arms=None, cells=("core",), limit: int | None = None) -> list[dict]:
    rows = []
    for line in Path(path).read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        m = r["metadata"]
        if m["cell"] not in cells or (arms and m["arm"] not in arms):
            continue
        rows.append(r)
    if limit:
        rows = rows[:limit]
    return rows


@dataclass(frozen=True)
class GridItem:
    model: str          # label: base | sft
    row_id: str
    idx: int = 0

    @property
    def id(self) -> str:
        return f"{self.model}|{self.row_id}"


def enumerate_items(rows, models=("base", "sft"), n: int = 1) -> list[tuple[GridItem, dict]]:
    return [(GridItem(m, r["id"], i), r) for m in models for r in rows for i in range(n)]


def sample_seed(run_seed: int, item: GridItem) -> int:
    return int(hashlib.sha256(f"{run_seed}|{item.id}|{item.idx}".encode()).hexdigest()[:8], 16) % (2**31 - 1)


def episode_from_row(row: dict):
    """A harness Episode rebuilt from an export row (the prompt text is already rendered; no tokenizer needed)."""
    from harness.episode import Episode
    from scorers.trl_adapter import to_served
    m = row["metadata"]
    return Episode(messages=row["input"], prompt_text=row["prompt_text"], served=to_served(m["served"]),
                   prefill=row.get("prefill", ""), meta={"scenario": m.get("scenario"), "arm": m["arm"],
                                                         "settings": m.get("settings", {})})


# ------------------------------------------------------------------ backend (injectable for tests)
@dataclass
class GridBackend:
    arun: Callable        # async (ep, settings) -> Completion
    score: Callable       # (parsed, key, served, judge) -> dict
    make_settings: Callable


def default_backend() -> GridBackend:
    import harness
    from .core import score_reply_with_details
    return GridBackend(harness.arun_episode, score_reply_with_details, harness.HarnessSettings)


def copy_case(key: AnswerKey, served) -> dict:
    """Copy-the-case baseline: the served card's verdict, translated to the live option ids through the key's option map
    (PDF falsification test 4). Unavailable without a card or a map (arm none, decoy). An untranslatable verdict is wrong."""
    out = {"copy_available": False, "copy_correct": None}
    if not served or not key.option_map:
        return out
    try:
        s = served[0]
        ch = s.doc["case"]["verdict"]["choice"]
        live = [o for o, c in key.option_map.items() if c == s.table.get(ch)]
    except Exception:
        return out
    out["copy_available"] = True
    out["copy_correct"] = bool(len(live) == 1 and key.correct(live[0]))
    return out


def make_record(run_id: str, item: GridItem, row: dict, seed: int, out, parsed, scores, score_error, raw_rel, key: AnswerKey,
                served=None) -> dict:
    m = row["metadata"]
    s = scores or {}
    verdict = parsed.steps.get("verdict", {}) or {}
    fe = parsed.steps.get("fact_enumeration", {}) or {}
    opts = list((fe.get("options") or {}).keys()) if isinstance(fe.get("options"), dict) else []
    choice = verdict.get("choice")
    tc = score_names.get(s, "translated_choice")
    cs = score_names.get(s, "choice")
    correct = 0.0 if choice is None else (None if cs is None else float(cs))
    chosen = key.options.get(tc) if tc else None
    gold = key.options[key.choice]
    return {
        "run_id": run_id, "sample_id": f"{item.id}|{item.idx}", "model": item.model, "row_id": item.row_id, "sample_idx": item.idx,
        "seed": seed, "pair": m["pair"], "arm": m["arm"], "cell": m["cell"], "card_view": m["card_view"], "ar": m["AR"],
        "equities_on": m["equities_on"], "intent": m["intent"], "relation": m["relation"], "realization": m.get("realization"),
        "tier": m["tier"], "family": m["family"], "domain": m.get("domain"), "held_out": bool(m.get("held_out")),
        "split": m["split"], "tags": m.get("tags", []), "d": m.get("d"), "trace_relevant_d": m.get("trace_relevant_d"),
        "restyle_partner": m.get("restyle_partner"), "scenario": m["scenario"], "case": m.get("case"),
        "recommended_option": m.get("recommended_option"),
        "parsed_choice": choice, "translated_choice": tc, "gold_choice": key.choice, "correct": correct,
        "off_menu": bool(choice is not None and tc is None),
        "gold_option_present": score_names.get(s, "gold_option_present"),
        "gold_move": gold.move, "gold_irreversible": gold.irreversible,
        "chosen_move": chosen.move if chosen else None, "chosen_irreversible": chosen.irreversible if chosen else None,
        "model_relation": verdict.get("relation"), "gold_relation": key.relation,
        "n_model_options": len(opts), "scores": scores, "score_error": score_error,
        "tokens": usage_tokens(out, out.raw_text), "seconds": getattr(out, "seconds", None),
        "finish_reason": getattr(out, "finish_reason", None), "format": format_report(parsed),
        "cues": gold_cues(key), **copy_case(key, served), "raw_path": raw_rel, "ts": time.time()}


async def run_one(ctx: dict, item: GridItem, row: dict, done: set) -> dict | None:
    if item.id + f"|{item.idx}" in done:
        return None
    be: GridBackend = ctx["backend"]
    run_dir: Path = ctx["run_dir"]
    try:
        seed = sample_seed(ctx["seed"], item)
        settings = be.make_settings(mode=MODE, analogical_prompt=row["metadata"]["AR"], max_tokens=ctx["max_tokens"],
                                    seed=seed, model=MODELS[item.model])
        ep = episode_from_row(row)
        async with ctx["sem"]:
            out = await be.arun(ep, settings)
        raw = out.raw_text
        arm = row["metadata"]["arm"]
        parsed = parse_reply(raw, noref=arm == "none")
        key = AnswerKey.model_validate(row["metadata"]["answer_key"])
        scores, err = None, None
        try:
            scores = await asyncio.to_thread(be.score, parsed, key, ep.served, ctx["judge"])
        except Exception as e:                         # judge down: keep the sample, rescore later
            err = f"{type(e).__name__}: {e}"
        rel = f"raw/{safe_name(item.id)}__{item.idx}.txt"
        (run_dir / rel).write_text(raw)
        rec = make_record(ctx["run_id"], item, row, seed, out, parsed, scores, err, rel, key, ep.served)
        async with ctx["lock"]:
            with open(run_dir / "samples.jsonl", "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        done.add(rec["sample_id"])
        return rec
    except Exception as e:
        with open(run_dir / "errors.jsonl", "a") as f:
            f.write(json.dumps({"sample_id": f"{item.id}|{item.idx}", "error": f"{type(e).__name__}: {e}", "ts": time.time()}) + "\n")
        return None


async def run_grid(rows, run_dir, *, backend: GridBackend, judge: Any, models=("base", "sft"), n: int = 1,
                   concurrency: int = 24, max_tokens: int | None = 8000, run_seed: int = 0, progress_every: int = 25) -> dict:
    run_dir = Path(run_dir)
    (run_dir / "raw").mkdir(parents=True, exist_ok=True)
    done = {r["sample_id"] for r in read_samples(run_dir / "samples.jsonl")}
    todo = [(it, r) for it, r in enumerate_items(rows, models, n) if f"{it.id}|{it.idx}" not in done]
    ctx = {"backend": backend, "judge": judge, "run_dir": run_dir, "run_id": run_dir.name, "seed": run_seed,
           "max_tokens": max_tokens, "sem": asyncio.Semaphore(concurrency), "lock": asyncio.Lock()}
    t0, k = time.time(), 0
    tasks = [asyncio.create_task(run_one(ctx, it, r, done)) for it, r in todo]
    for fut in asyncio.as_completed(tasks):
        await fut
        k += 1
        if progress_every and k % progress_every == 0:
            print(f"{k}/{len(tasks)} done, {time.time() - t0:.0f}s", file=sys.stderr)
    errs = (run_dir / "errors.jsonl")
    m = {"run_id": run_dir.name, "models": list(models), "n": n, "mode": MODE, "total": len(todo) + len(done),
         "skipped_done": len(done), "ran": len(todo), "concurrency": concurrency, "max_tokens": max_tokens,
         "served_models": {k: MODELS[k] for k in models}, "seconds": round(time.time() - t0, 1),
         "errors": sum(1 for _ in errs.open()) if errs.exists() else 0, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    (run_dir / f"manifest.{time.strftime('%Y%m%dT%H%M%S')}.json").write_text(json.dumps(m, indent=1))
    return m


def rescore_grid(rows, run_dir, *, score: Callable, judge: Any, workers: int = 16) -> dict:
    """Re-parse each saved raw reply and re-score it; tokens, seconds, finish reason and seed are kept from the old record."""
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace
    from scorers.trl_adapter import to_served
    run_dir = Path(run_dir)
    sp = run_dir / "samples.jsonl"
    old = [json.loads(l) for l in sp.read_text().splitlines() if l.strip()]
    by_id = {r["id"]: r for r in rows}

    def one(rec):
        row, raw_p = by_id.get(rec["row_id"]), run_dir / rec["raw_path"]
        if row is None or not raw_p.exists():
            return rec, "kept (no export row or raw file)"
        m = row["metadata"]
        parsed = parse_reply(raw_p.read_text(), noref=m["arm"] == "none")
        key, served = AnswerKey.model_validate(m["answer_key"]), to_served(m["served"])
        scores, err = None, None
        try:
            scores = score(parsed, key, served, judge)
        except Exception as e:                         # noqa: BLE001
            err = f"{type(e).__name__}: {e}"
        out = SimpleNamespace(raw_text="", seconds=rec.get("seconds"), finish_reason=rec.get("finish_reason"))
        new = make_record(rec["run_id"], GridItem(rec["model"], rec["row_id"], rec["sample_idx"]), row, rec["seed"], out,
                          parsed, scores, err, rec["raw_path"], key, served)
        new.update(tokens=rec.get("tokens"), ts=rec.get("ts"), rescored=time.time())
        return new, "rescored" if err is None else "score error"

    with ThreadPoolExecutor(workers) as ex:
        res = list(ex.map(one, old))
    vdir = run_dir / "versions"
    vdir.mkdir(exist_ok=True)
    shutil.copy2(sp, vdir / f"samples.{time.strftime('%Y%m%dT%H%M%S')}-before-rescore.jsonl")
    sp.write_text("".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r, _ in res))
    return dict(Counter(s for _, s in res))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--export", default="data/exports/v1/eval/inspect.jsonl")
    ap.add_argument("--run", required=True, help="run dir, e.g. results/eval-v1/run1 (resumable)")
    ap.add_argument("--models", nargs="+", default=["base", "sft"], choices=list(MODELS))
    ap.add_argument("--arms", nargs="+", choices=GRID_ARMS)
    ap.add_argument("--cells", nargs="+", default=["core"], choices=CELLS, help="default: core only (second-pass cells are opt-in)")
    ap.add_argument("-n", type=int, default=1)
    ap.add_argument("--concurrency", type=int, default=24)
    ap.add_argument("--max-tokens", type=int, default=8000)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--judge", default="jev", choices=["jev", "stub"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--rescore", action="store_true", help="re-parse and re-score saved replies (no generation)")
    a = ap.parse_args(argv)
    from .core import default_judge
    rows = load_export(a.export, a.arms, tuple(a.cells), a.limit)
    if not rows:
        raise SystemExit(f"no rows in {a.export} for arms={a.arms} cells={a.cells}")
    if a.rescore:
        print(json.dumps(rescore_grid(rows, a.run, score=default_backend().score, judge=default_judge(a.judge))))
        return 0
    m = asyncio.run(run_grid(rows, a.run, backend=default_backend(), judge=default_judge(a.judge), models=tuple(a.models),
                             n=a.n, concurrency=a.concurrency, max_tokens=a.max_tokens, run_seed=a.seed))
    print(json.dumps(m, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
