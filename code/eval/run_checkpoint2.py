"""Checkpoint 2 without Inspect: a plain asyncio runner writing the same results/checkpoint2/<run>/samples.jsonl.

    PYTHONPATH=code .venv/bin/python -m eval.run_checkpoint2 --run-id pilot-v1 --samples 5 --concurrency 16
    ... --modes A B --arms relevant decoy --prompts on --limit-scenarios 2 --judge stub     # a small slice
Resumable: re-running with the same --run-id skips (item, sample_idx) pairs already in samples.jsonl.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

from . import core
from .core import Context, Item


def add_grid_args(ap: argparse.ArgumentParser):
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--results-dir", default="results/checkpoint2")
    ap.add_argument("--run-id", default=time.strftime("ckpt2-%Y%m%d-%H%M%S"))
    ap.add_argument("--samples", type=int, default=5, help="samples per item (PDF/Decisions: 5-8)")
    ap.add_argument("--concurrency", type=int, default=16, help="max in-flight policy requests")
    ap.add_argument("--modes", nargs="+", default=list(core.MODES), choices=core.MODES)
    ap.add_argument("--arms", nargs="+", default=None, choices=core.ARMS, help="default: all arms each scenario has")
    ap.add_argument("--prompts", choices=["both", "on", "off"], default="both", help="analogical-reasoning prompt")
    ap.add_argument("--scenarios", nargs="+", default=None, help="scenario ids")
    ap.add_argument("--family", nargs="+", default=None)
    ap.add_argument("--split", default=None)
    ap.add_argument("--limit-scenarios", type=int, default=None)
    ap.add_argument("--max-tokens", type=int, default=None, help="default: role(policy).max_tokens (12000)")
    ap.add_argument("--run-seed", type=int, default=0)
    ap.add_argument("--judge", choices=["jev", "stub"], default="jev")
    ap.add_argument("--injection-role", default=None)
    ap.add_argument("--tool-messages", default=None, choices=[None, "flattened", "native"])


def load_scenarios(lib, args):
    scs = lib.scenarios(split=args.split) if args.split else lib.scenarios()
    if args.family:
        scs = [s for s in scs if s.family in args.family]
    if args.scenarios:
        scs = [s for s in scs if s.id in args.scenarios]
    scs = sorted(scs, key=lambda s: s.id)
    return scs[: args.limit_scenarios] if args.limit_scenarios else scs


def settings_extra(args) -> dict:
    d = {}
    if args.injection_role:
        d["injection_role"] = args.injection_role
    if args.tool_messages:
        d["tool_messages"] = args.tool_messages
    return d


def prompts_of(args):
    return {"both": (True, False), "on": (True,), "off": (False,)}[args.prompts]


def make_context(args, lib=None, backend=None, judge=None) -> tuple[Context, list[Item]]:
    if lib is None:
        from library import Library
        lib = Library(root=args.data_root)
    scs = load_scenarios(lib, args)
    ctx = Context(lib=lib, backend=backend or core.default_backend(),
                  judge=judge if judge is not None else core.default_judge(args.judge),
                  run_dir=Path(args.results_dir) / args.run_id, run_id=args.run_id, run_seed=args.run_seed,
                  max_tokens=args.max_tokens, settings_extra=settings_extra(args),
                  scenarios={s.id: s for s in scs}, concurrency=args.concurrency)
    items = core.enumerate_items(scs, args.arms, prompts_of(args), args.modes)
    return ctx, items


async def run_all(ctx: Context, items: list[Item], n_samples: int, progress: bool = True) -> int:
    done = core.done_keys(ctx.samples_path)
    todo = [(it, i) for it in items for i in range(n_samples) if (it.id, i) not in done]
    print(f"[ckpt2] run {ctx.run_id}: {len(items)} items x {n_samples} = {core.total_samples(items, n_samples)} samples; "
          f"{len(done)} done, {len(todo)} to run, concurrency {ctx.concurrency}", file=sys.stderr)
    q: asyncio.Queue = asyncio.Queue()
    for t in todo:
        q.put_nowait(t)
    n_ok = 0
    t0 = time.time()

    async def worker():
        nonlocal n_ok
        while True:
            try:
                it, i = q.get_nowait()
            except asyncio.QueueEmpty:
                return
            rec = await core.run_sample(ctx, it, i, done)
            n_ok += rec is not None
            if progress and rec is not None and n_ok % 10 == 0:
                print(f"[ckpt2] {n_ok}/{len(todo)} ({time.time() - t0:.0f}s)", file=sys.stderr)

    await asyncio.gather(*[worker() for _ in range(max(1, ctx.concurrency))])
    if len(todo) - n_ok:
        print(f"[ckpt2] {len(todo) - n_ok} samples failed; see {ctx.run_dir}/errors.jsonl (re-run to retry)", file=sys.stderr)
    return n_ok


def main(argv=None, lib=None, backend=None, judge=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_grid_args(ap)
    ap.add_argument("--rescore", action="store_true", help="re-score samples whose scoring failed (no generation)")
    args = ap.parse_args(argv)
    ctx, items = make_context(args, lib, backend, judge)
    core.write_manifest(ctx, items, args.samples)
    if args.rescore:
        print(f"rescored {core.rescore(ctx)} samples")
        return 0
    asyncio.run(run_all(ctx, items, args.samples))
    return 0


if __name__ == "__main__":
    sys.exit(main())
