"""Checkpoint 2 as an Inspect task (UK AISI inspect_ai).

Dataset  = scenarios x arms present x analogical prompt {on, off} x mode {A, B, C, Cprime};  epochs = samples/item.
Solver   = custom: runs the episode through the harness (the policy is reached via harness -> vLLM, NOT through
           Inspect's model API; run Inspect with `--model mockllm/model`), parses, scores with 2d's `score_reply`,
           appends the full record to results/checkpoint2/<run>/samples.jsonl (same file the asyncio runner writes).
Scorer   = reads the scores the solver computed (so the JSONL and the Inspect log can never disagree) and returns
           them as a dict-valued Inspect Score; every numeric scorer gets its own mean/stderr column.
Resume   = items fully present in samples.jsonl are dropped from the dataset; partly-done items skip finished epochs.

    PYTHONPATH=code .venv/bin/python -m eval.checkpoint2 --run-id pilot-v1 --samples 5 --concurrency 16
    # or:  inspect eval code/eval/checkpoint2.py@checkpoint2 --model mockllm/model -T run_id=pilot-v1 -T samples=5
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import asdict
from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample
from inspect_ai.model import ModelOutput
from inspect_ai.scorer import Score, Target, mean, scorer, stderr
from inspect_ai.solver import Generate, TaskState, solver

from . import core, score_names
from .core import Context, Item


@solver
def harness_solver(ctx: Context):
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        item = Item(**state.metadata["item"])
        idx = state.epoch - 1
        rec = state.metadata.get("_existing", {}).get(idx)
        if rec is None:
            done = core.done_keys(ctx.samples_path)
            if (item.id, idx) in done:
                rec = next(r for r in core.read_samples(ctx.samples_path)
                           if r["item_id"] == item.id and r["sample_idx"] == idx)
            else:
                rec = await core.run_sample(ctx, item, idx, done)
        state.metadata["record"] = rec
        raw = ""
        if rec:
            p = ctx.run_dir / rec["raw_path"]
            raw = p.read_text() if p.exists() else ""
        state.output = ModelOutput.from_content("harness/policy", raw)
        return state
    return solve


LOGICAL = ("choice", "relation", "via", "options_enumeration", "options_omitted")   # score_names keys shown in Inspect


@scorer(metrics={"*": [mean(), stderr()]})
def record_scorer():
    async def score(state: TaskState, target: Target) -> Score:
        rec = state.metadata.get("record")
        nan = float("nan")     # Inspect needs identical keys every epoch; NaN = "not scored"
        if not rec:
            return Score(value={**{k: nan for k in LOGICAL}, "strict_ok": nan, "errored": 1.0},
                         explanation="harness/scoring failed; see errors.jsonl")
        vals = {}
        for k in LOGICAL:
            v = score_names.get(rec.get("scores"), k)
            vals[k] = nan if v is None else float(v)
        if rec.get("parsed_choice") is None:
            vals["choice"] = 0.0       # no verdict = wrong (same rule as eval.stats.choice_correct)
        vals["strict_ok"] = float(rec["format"]["strict_ok"])
        vals["errored"] = 0.0
        return Score(value=vals, answer=str(rec.get("parsed_choice")),
                     explanation=f"gold {rec['gold_choice']}; relation {rec.get('relation')}",
                     metadata={"sample_idx": rec["sample_idx"], "raw_path": rec["raw_path"], "seed": rec["seed"]})
    return score


def build_dataset(ctx: Context, items: list[Item], n_samples: int) -> MemoryDataset:
    recs = core.read_samples(ctx.samples_path)
    have: dict[str, dict[int, dict]] = {}
    for r in recs:
        have.setdefault(r["item_id"], {})[r["sample_idx"]] = r
    samples = []
    for it in items:
        ex = have.get(it.id, {})
        if all(i in ex for i in range(n_samples)):
            continue
        sc = ctx.scenarios[it.scenario]
        samples.append(Sample(
            input=f"{it.scenario} arm={it.arm} prompt={it.prompt} mode={it.mode}", id=it.id,
            metadata={"item": asdict(it), "family": sc.family, "variant": sc.perturbation.variant,
                      "_existing": {}}))
    return MemoryDataset(samples, name="checkpoint2")


def make_task(ctx: Context, items: list[Item], n_samples: int) -> Task:
    return Task(dataset=build_dataset(ctx, items, n_samples), solver=harness_solver(ctx), scorer=record_scorer(),
                epochs=n_samples, name="checkpoint2", metadata={"run_id": ctx.run_id})


@task
def checkpoint2(run_id: str = "ckpt2-inspect", samples: int = 5, concurrency: int = 16, data_root: str = "data",
                results_dir: str = "results/checkpoint2", modes: str = "A,B,C,Cprime", arms: str = "",
                prompts: str = "both", judge: str = "jev", max_tokens: int | None = None, run_seed: int = 0,
                limit_scenarios: int | None = None) -> Task:
    """`inspect eval` entry point (all arguments are strings/ints, pass with -T)."""
    from .run_checkpoint2 import make_context
    ns = argparse.Namespace(data_root=data_root, results_dir=results_dir, run_id=run_id, samples=samples,
                            concurrency=concurrency, modes=modes.split(","), arms=arms.split(",") if arms else None,
                            prompts=prompts, scenarios=None, family=None, split=None, limit_scenarios=limit_scenarios,
                            max_tokens=max_tokens, run_seed=run_seed, judge=judge, injection_role=None,
                            tool_messages=None)
    ctx, items = make_context(ns)
    core.write_manifest(ctx, items, samples, {"runner": "inspect"})
    return make_task(ctx, items, samples)


def main(argv=None, lib=None, backend=None, judge=None, log_dir: str | None = None):
    from inspect_ai import eval as inspect_eval

    from .run_checkpoint2 import add_grid_args, make_context
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_grid_args(ap)
    ap.add_argument("--log-dir", default=None)
    args = ap.parse_args(argv)
    ctx, items = make_context(args, lib, backend, judge)
    core.write_manifest(ctx, items, args.samples, {"runner": "inspect"})
    if len(build_dataset(ctx, items, args.samples)) == 0:
        print("[ckpt2] nothing left to run (all items complete in samples.jsonl)", file=sys.stderr)
        return 0
    t = make_task(ctx, items, args.samples)
    logs = inspect_eval(t, model="mockllm/model", max_samples=args.concurrency, max_tasks=1,
                        log_dir=log_dir or args.log_dir or str(ctx.run_dir / "inspect_logs"), display="plain",
                        fail_on_error=False)
    return 0 if logs and logs[0].status == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
