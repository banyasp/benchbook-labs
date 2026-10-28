"""Faithfulness / manipulation test (PDF p. 29, "Manipulation of analogical reasoning"; DECISIONS Checkpoint 2).

For a subset of completed samples whose mapping steps parsed, edit the partial reply BEFORE the verdict, let the
model continue from the edited text (`harness.continue_episode`), and record whether `verdict.choice` changes:

  control        unedited partial, regenerated from the cut  (sampling noise: the floor for "change")
  weight_flip    the decisive consideration's weight strong<->weak in consideration_enumeration
  to_case_only   the decisive consideration's pair removed from consideration_mapping.matched; the case item goes
                 to case_only (the live item disappears from the mapping)
  to_live_only   same, but the live item goes to live_only (the case item disappears)
  swap_revised   re-run from fact_mapping with the arm's revised card (arm `augmented`) served instead of the
                 relevant card (only for scenarios that have an augmented arm)

`--resume-at verdict` (default) regenerates only the verdict; `reasoning` also regenerates the reasoning step;
`edit` resumes right after the edited step (the model redoes everything downstream). The decisive consideration is
the first id in the sample's own verdict.decisive.  Prediction under test: mode A is the least sensitive.

    PYTHONPATH=code .venv/bin/python -m eval.faithfulness results/checkpoint2/<run> --max-samples 60 --reps 1
Output: <run>/faithfulness.jsonl (one row per sample x intervention x rep) and <run>/faithfulness_summary.json.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import yaml
from bench.schema import parse_reply
from bench.schema.reply import KIND_LINE, STOP_LINE, TOP_KEY

from . import core, stats
from .core import Context, Item

INTERVENTIONS = ("control", "weight_flip", "to_case_only", "to_live_only", "swap_revised")
RESUME_AT = ("verdict", "reasoning", "edit")


# ------------------------------------------------------------------ text surgery on the raw reply
def doc_spans(text: str) -> list[dict]:
    """Character spans of every `kind:` document in the raw reply (same chunking rule as bench's parser)."""
    lines = text.splitlines(keepends=True)
    offs, o = [], 0
    for ln in lines:
        offs.append(o)
        o += len(ln)
    offs.append(o)
    starts = [i for i, ln in enumerate(lines) if KIND_LINE.match(ln.rstrip("\n"))]
    spans = []
    for n, s in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        stop = end
        for j in range(s + 1, end):
            raw = lines[j].rstrip("\n")
            if STOP_LINE.match(raw) or (raw[:1].strip() and not TOP_KEY.match(raw) and not raw.startswith("#")):
                stop = j
                break
        kind = KIND_LINE.match(lines[s].rstrip("\n")).group(1)
        spans.append({"kind": kind, "start": offs[s], "end": offs[stop], "line": s})
    return spans


def last_span(text: str, kind: str) -> dict | None:
    sp = [s for s in doc_spans(text) if s["kind"] == kind]
    return sp[-1] if sp else None


class _IndentedDumper(yaml.SafeDumper):
    """Indent block sequences under their key: bench's parser ends a document at a column-0 line that is not a
    `snake_case_key:` (a `- item` at column 0 would read as prose)."""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def _dump(d: dict) -> str:
    return yaml.dump(d, Dumper=_IndentedDumper, sort_keys=False, allow_unicode=True, width=140,
                     default_flow_style=False)


def _replace_doc(text: str, kind: str, mutate) -> str | None:
    sp = last_span(text, kind)
    if sp is None:
        return None
    chunk = text[sp["start"]: sp["end"]]
    try:
        d = yaml.safe_load(chunk)
    except yaml.YAMLError:                 # the reply parsed only with recorded repairs: use the same repairs
        from bench.schema.reply import _load
        d = _load(chunk.splitlines())[0]
    if not isinstance(d, dict) or mutate(d) is False:
        return None
    return text[: sp["start"]] + _dump(d) + text[sp["end"]:]


def edit_weight_flip(text: str, cid: str) -> str | None:
    def m(d):
        for c in d.get("considerations") or []:
            if c.get("id") == cid:
                c["weight"] = "weak" if c.get("weight") in ("strong", "bar") else "strong"
                return True
        return False
    return _replace_doc(text, "consideration_enumeration", m)


def edit_move_matched(text: str, cid: str, to: str) -> str | None:
    assert to in ("case_only", "live_only")

    def m(d):
        pairs = d.get("matched") or []
        hit = [p for p in pairs if p.get("live") == cid]
        if not hit:
            return False
        d["matched"] = [p for p in pairs if p.get("live") != cid]
        if to == "case_only":
            d["case_only"] = list(d.get("case_only") or []) + [hit[0]["case"]]
        else:
            d["live_only"] = list(d.get("live_only") or []) + [cid]
        return True
    return _replace_doc(text, "consideration_mapping", m)


def cut_before(text: str, kind: str) -> str | None:
    sp = last_span(text, kind)
    return None if sp is None else text[: sp["start"]]


def cut_after(text: str, kind: str) -> str | None:
    sp = last_span(text, kind)
    return None if sp is None else text[: sp["end"]].rstrip("\n") + "\n---\n"


def apply(intervention: str, raw: str, decisive: str, resume_at: str) -> str | None:
    """The edited partial reply (ready for continue_episode), or None if the intervention does not apply."""
    if intervention == "control":
        edited = raw
    elif intervention == "weight_flip":
        edited = edit_weight_flip(raw, decisive)
    elif intervention in ("to_case_only", "to_live_only"):
        edited = edit_move_matched(raw, decisive, intervention.removeprefix("to_"))
    elif intervention == "swap_revised":
        return cut_before(raw, "fact_mapping")
    else:
        raise ValueError(intervention)
    if edited is None:
        return None
    if resume_at == "edit":
        kind = {"control": "fact_enumeration", "weight_flip": "consideration_enumeration"}.get(intervention, "consideration_mapping")
        return cut_after(edited, kind)
    return cut_before(edited, resume_at)


def full_text(partial: str, out) -> str:
    """harness.continue_episode: raw_text of the result = partial (opener prepended if missing) + new text."""
    return out.raw_text


# ------------------------------------------------------------------ selection
def eligible(rec: dict) -> bool:
    f = rec["format"]
    need = {"consideration_enumeration", "fact_mapping", "consideration_mapping", "verdict"}
    return need <= set(f["steps_present"]) and not {k for k in need if k in f["errors"]} and rec["relation"] != "not_governed"


def select(recs, arms, modes, max_samples, seed=0) -> list[dict]:
    pool = [r for r in recs if eligible(r) and r["arm"] in arms and r["mode"] in modes]
    rng = random.Random(seed)
    by_mode = defaultdict(list)
    for r in pool:
        by_mode[r["mode"]].append(r)
    out = []
    per = max(1, max_samples // max(1, len(by_mode))) if max_samples else None
    for m in sorted(by_mode):
        v = by_mode[m]
        rng.shuffle(v)
        out += v[:per] if per else v
    return out


# ------------------------------------------------------------------ run
async def one(ctx: Context, rec: dict, interv: str, rep: int, resume_at: str) -> dict | None:
    item = Item(rec["scenario"], rec["arm"], rec["analogical_prompt"], rec["mode"])
    raw = (ctx.run_dir / rec["raw_path"]).read_text()
    parsed = parse_reply(raw, noref=item.arm == "none")
    dec = (parsed.steps["verdict"].get("decisive") or [None])[0]
    if interv != "control" and interv != "swap_revised" and dec is None:
        return None
    sc = ctx.scenarios[item.scenario]
    arm = item.arm
    if interv == "swap_revised":
        if "augmented" not in sc.arms or item.arm != "relevant":
            return None
        arm = "augmented"
    try:
        partial = apply(interv, raw, dec, resume_at if interv != "swap_revised" else "verdict")
    except Exception:                      # one unusable reply must not end the run; it is simply not eligible
        return None
    if partial is None:
        return None
    seed = (core.sample_seed(ctx.run_seed, item, rec["sample_idx"]) + 1000 * (rep + 1) + INTERVENTIONS.index(interv)) % (2**31 - 1)
    row = {"item_id": item.id, "scenario": item.scenario, "family": rec["family"], "arm": item.arm, "mode": item.mode,
           "analogical_prompt": item.prompt, "sample_idx": rec["sample_idx"], "intervention": interv, "rep": rep,
           "resume_at": resume_at, "decisive": dec, "orig_choice": rec["parsed_choice"], "seed": seed}
    try:
        async with ctx.sem:
            st = ctx.settings(item, seed)
            ep = ctx.backend.build_episode(sc, arm, st, ctx.lib)
            out = await ctx.backend.cont(ep, st, partial)
        new = parse_reply(full_text(partial, out)).steps.get("verdict") or {}
        row.update(new_choice=new.get("choice"), new_relation=new.get("relation"),
                   changed=None if new.get("choice") is None else bool(new.get("choice") != rec["parsed_choice"]),
                   target_arm=arm, finish_reason=getattr(out, "finish_reason", None))
    except Exception as e:
        row["error"] = f"{type(e).__name__}: {e}"
    return row


async def run_faithfulness(ctx: Context, recs, interventions, reps, resume_at) -> list[dict]:
    path = ctx.run_dir / "faithfulness.jsonl"
    done = {(r["item_id"], r["sample_idx"], r["intervention"], r["rep"], r["resume_at"])
            for r in core.read_samples(path) if "error" not in r}
    todo = [(r, iv, k) for r in recs for iv in interventions for k in range(reps)
            if (r["item_id"], r["sample_idx"], iv, k, resume_at) not in done]
    lock = asyncio.Lock()
    rows = []

    async def go(r, iv, k):
        row = await one(ctx, r, iv, k, resume_at)
        if row is None:
            return
        async with lock:
            with open(path, "a") as f:
                f.write(json.dumps(row, default=str) + "\n")
        rows.append(row)

    await asyncio.gather(*[go(*t) for t in todo])
    return rows


# ------------------------------------------------------------------ summary
def summarize(rows, n_boot=stats.N_BOOT) -> dict:
    """Change rate per mode x intervention, family-bootstrap CI, and excess over the control (sampling noise)."""
    ok = [r for r in rows if r.get("changed") is not None]
    out = {}
    for mode in core.MODES:
        for iv in INTERVENTIONS:
            sub = [r for r in ok if r["mode"] == mode and r["intervention"] == iv]
            if not sub:
                continue
            f = lambda r: float(r["changed"])   # noqa: E731
            cell = stats.family_bootstrap(sub, f, n_boot)
            ctrl = [r for r in ok if r["mode"] == mode and r["intervention"] == "control"]
            if iv != "control" and ctrl:
                cell["excess_over_control"] = stats.family_bootstrap_diff(sub, ctrl, f, n_boot)
            cell["n_no_verdict"] = sum(1 for r in rows if r["mode"] == mode and r["intervention"] == iv
                                       and r.get("changed") is None)
            out[f"{mode}|{iv}"] = cell
    return out


def main(argv=None, lib=None, backend=None, judge=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir")
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--max-samples", type=int, default=60, help="total completed samples to intervene on (split over modes)")
    ap.add_argument("--arms", nargs="+", default=["relevant"])
    ap.add_argument("--modes", nargs="+", default=list(core.MODES))
    ap.add_argument("--interventions", nargs="+", default=list(INTERVENTIONS), choices=INTERVENTIONS)
    ap.add_argument("--reps", type=int, default=1, help="continuations per sample x intervention")
    ap.add_argument("--resume-at", choices=RESUME_AT, default="verdict")
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--judge", choices=["jev", "stub"], default="stub", help="unused unless scoring is added")
    ap.add_argument("--summarize-only", action="store_true")
    a = ap.parse_args(argv)
    run_dir = Path(a.run_dir)
    man = json.loads((run_dir / "manifest.json").read_text())
    if lib is None:
        from library import Library
        lib = Library(root=a.data_root)
    ctx = Context(lib=lib, backend=backend or core.default_backend(),
                  judge=judge, run_dir=run_dir, run_id=man["run_id"], run_seed=man.get("run_seed", 0),
                  max_tokens=man.get("max_tokens"), settings_extra=man.get("settings_extra") or {},
                  concurrency=a.concurrency)
    path = run_dir / "faithfulness.jsonl"
    if not a.summarize_only:
        recs = select(core.read_samples(run_dir / "samples.jsonl"), set(a.arms), set(a.modes), a.max_samples, a.seed)
        print(f"[faithfulness] {len(recs)} eligible samples x {len(a.interventions)} interventions x {a.reps}", file=sys.stderr)
        asyncio.run(run_faithfulness(ctx, recs, a.interventions, a.reps, a.resume_at))
    s = summarize(core.read_samples(path))
    (run_dir / "faithfulness_summary.json").write_text(json.dumps(s, indent=2, default=str))
    for k, v in s.items():
        print(f"{k:28s} change {v['mean']:.2f} [{v['lo']:.2f}, {v['hi']:.2f}] n={v['n']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
