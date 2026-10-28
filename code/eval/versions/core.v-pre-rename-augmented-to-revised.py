"""Shared core of the Checkpoint 2 runners (Inspect task and plain asyncio runner write the same JSONL).

Grid: scenarios x arms present for the scenario x analogical prompt {on, off} x mode {A, B, C, Cprime}
      x samples (idx 0..n-1).   total = n_samples * sum over scenarios of (#arms * #prompts * #modes).

Everything that touches 2b/2c/2d goes through `Backend` so tests can inject fakes; `default_backend()` wires the
real packages (imported lazily, so importing this module needs neither vLLM nor the judge).
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from bench.schema import parse_reply

from . import score_names

MODES = ("A", "B", "C", "Cprime")
ARMS = ("none", "relevant", "augmented", "decoy")
# eval-side mode name -> the string HarnessSettings(mode=...) expects. Adjust here if 2c spells C' differently.
HARNESS_MODE = {"A": "A", "B": "B", "C": "C", "Cprime": "Cprime"}
SCHEMA_VERSION = 1


# ------------------------------------------------------------------ grid
@dataclass(frozen=True)
class Item:
    scenario: str
    arm: str
    prompt: bool
    mode: str

    @property
    def id(self) -> str:
        return f"{self.scenario}|{self.arm}|{'prompt' if self.prompt else 'noprompt'}|{self.mode}"


def enumerate_items(scenarios, arms=None, prompts=(True, False), modes=MODES) -> list[Item]:
    items = []
    for sc in scenarios:
        for arm in sc.arms:
            if arms and arm not in arms:
                continue
            for p in prompts:
                for m in modes:
                    items.append(Item(sc.id, arm, p, m))
    return items


def sample_seed(run_seed: int, item: Item, idx: int) -> int:
    h = hashlib.sha256(f"{run_seed}|{item.id}|{idx}".encode()).hexdigest()
    return int(h[:8], 16) % (2**31 - 1)


def total_samples(items, n_samples: int) -> int:
    return len(items) * n_samples


def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)


# ------------------------------------------------------------------ backend (2b/2c/2d)
@dataclass
class Backend:
    build_episode: Callable            # (scenario, arm, settings, lib) -> Episode
    run_episode: Callable | None       # sync (ep, settings, role=...) -> Completion
    continue_episode: Callable | None  # sync (ep, settings, partial=...) -> Completion
    score_reply: Callable              # (parsed, key, served, judge) -> dict
    make_settings: Callable            # (**kw) -> HarnessSettings
    arun_episode: Callable | None = None
    acontinue_episode: Callable | None = None

    async def run(self, ep, settings, role="policy"):
        if self.arun_episode:
            return await self.arun_episode(ep, settings, role=role)
        return await asyncio.to_thread(self.run_episode, ep, settings, role=role)

    async def cont(self, ep, settings, partial):
        if self.acontinue_episode:
            return await self.acontinue_episode(ep, settings, partial=partial)
        return await asyncio.to_thread(self.continue_episode, ep, settings, partial=partial)


def score_reply_with_details(parsed, key, served, judge) -> dict:
    """2d's row dict plus two integration fields from its details: `translated_choice` (the gold option id the
    agent's choice was aligned to, None if unresolved) and `gold_option_present` (1 - options_correct_omitted)."""
    from scorers import score_reply_detailed
    r = score_reply_detailed(parsed, key, served, judge)
    rows = dict(r.rows)
    rows["translated_choice"] = ((r.details.get("notes") or {}).get("choice") or {}).get("gold_id")
    om = rows.get("options_correct_omitted")
    rows["gold_option_present"] = None if om is None else 1 - om
    return rows


def default_backend() -> Backend:
    import harness
    score_reply = score_reply_with_details
    return Backend(
        build_episode=harness.build_episode,
        run_episode=getattr(harness, "run_episode", None),
        continue_episode=getattr(harness, "continue_episode", None),
        score_reply=score_reply,
        make_settings=harness.HarnessSettings,
        arun_episode=getattr(harness, "arun_episode", None),
        acontinue_episode=getattr(harness, "acontinue_episode", None),
    )


def default_judge(kind: str = "jev", cache: str = "results/judge_cache.sqlite"):
    from scorers.judge import CachedJudge, JevJudge, StubJudge
    return StubJudge() if kind == "stub" else CachedJudge(JevJudge(), path=cache)


@dataclass
class Context:
    lib: Any
    backend: Backend
    judge: Any
    run_dir: Path
    run_id: str
    run_seed: int = 0
    max_tokens: int | None = None            # None -> role("policy") default (12000)
    settings_extra: dict = field(default_factory=dict)   # injection_role, tool_messages, ...
    scenarios: dict = field(default_factory=dict)
    concurrency: int = 16
    _sem: asyncio.Semaphore | None = None
    _lock: asyncio.Lock | None = None

    def __post_init__(self):
        self.run_dir = Path(self.run_dir)
        (self.run_dir / "raw").mkdir(parents=True, exist_ok=True)
        if not self.scenarios:
            self.scenarios = {s.id: s for s in self.lib.scenarios()}

    @property
    def sem(self):
        if self._sem is None:
            self._sem = asyncio.Semaphore(self.concurrency)
        return self._sem

    @property
    def lock(self):
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    @property
    def samples_path(self) -> Path:
        return self.run_dir / "samples.jsonl"

    def settings(self, item: Item, seed: int):
        return self.backend.make_settings(mode=HARNESS_MODE[item.mode], analogical_prompt=item.prompt,
                                          max_tokens=self.max_tokens, seed=seed, **self.settings_extra)


# ------------------------------------------------------------------ jsonl
def read_samples(path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass     # a torn last line from a killed run: the sample is simply redone
    return out


def done_keys(path) -> set[tuple[str, int]]:
    return {(r["item_id"], r["sample_idx"]) for r in read_samples(path)}


async def append_record(ctx: Context, rec: dict):
    async with ctx.lock:
        with open(ctx.samples_path, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")


def log_error(ctx: Context, item: Item, idx: int, exc: BaseException):
    with open(ctx.run_dir / "errors.jsonl", "a") as f:
        f.write(json.dumps({"item_id": item.id, "sample_idx": idx, "error": f"{type(exc).__name__}: {exc}",
                            "ts": time.time()}) + "\n")


# ------------------------------------------------------------------ record features
def perturbation_features(sc) -> dict:
    p = sc.perturbation
    by_kind, by_change, by_kc = Counter(), Counter(), Counter()
    for t in p.touched:
        by_kind[t.item_kind] += 1
        by_change[t.change] += 1
        by_kc[f"{t.item_kind}:{t.change}"] += 1
    return {"variant": p.variant, "operator": p.operator, "source_case": p.source_case,
            "domain_shift": p.domain_shift, "touched_total": len(p.touched), "touched_by_kind": dict(by_kind),
            "touched_by_change": dict(by_change), "touched_by_kind_change": dict(by_kc)}


def gold_cues(key) -> dict:
    """Shortcut-cue features of the gold: position of the gold option, move, option length vs the others."""
    ids = list(key.options)
    gold = key.options[key.choice]
    lens = {i: len(o.do) for i, o in key.options.items()}
    ranked = sorted(lens, key=lambda i: -lens[i])
    others = [v for i, v in lens.items() if i != key.choice]
    return {"gold_position": ids.index(key.choice), "n_gold_options": len(ids), "gold_move": gold.move,
            "gold_irreversible": gold.irreversible, "gold_len_chars": lens[key.choice],
            "gold_len_rank": ranked.index(key.choice), "gold_is_longest": ranked[0] == key.choice,
            "gold_is_shortest": ranked[-1] == key.choice,
            "mean_other_len": (sum(others) / len(others)) if others else None,
            "gold_is_hand_up": gold.move in ("ask", "refuse")}   # "hand up": escalate / ask / decline (Peter's cue)


def copy_baseline(key, lib) -> dict:
    """PDF falsification test 4: copy the served case's verdict, translated to the live gold option ids."""
    out = {"available": False, "choice": None, "correct": None}
    if not key.served or not key.option_map:
        return out
    try:
        case = lib.case(key.served)
        gid = case.global_id(case.verdict.choice)
    except Exception:
        return out
    live = [o for o, c in key.option_map.items() if c == gid]
    out["available"] = True
    out["case_choice"] = gid
    out["choice"] = live[0] if len(live) == 1 else None
    out["correct"] = bool(out["choice"] and key.correct(out["choice"]))   # untranslatable -> counts as wrong
    return out


def format_report(parsed) -> dict:
    return {"strict_ok": bool(parsed.strict_ok), "steps_present": sorted(parsed.steps), "n_steps": len(parsed.steps),
            "required": parsed.required(), "missing": parsed.missing, "errors": dict(parsed.errors),
            "n_repairs": sum(len(v) for v in parsed.repairs.values()), "in_order": parsed.in_order,
            "where": dict(parsed.where), "unknown_kinds": list(parsed.unknown_kinds),
            "n_unparsed": len(parsed.unparsed)}


def usage_tokens(out, raw_text: str) -> dict:
    u = getattr(out, "usage", None) or {}
    g = (lambda k: u.get(k)) if isinstance(u, dict) else (lambda k: getattr(u, k, None))
    think = g("reasoning_tokens") or g("thinking_tokens")
    if think is None:
        d = g("completion_tokens_details")
        think = (d.get("reasoning_tokens") if isinstance(d, dict) else getattr(d, "reasoning_tokens", None)) if d else None
    from bench.schema import split_think
    t, _ = split_think(getattr(out, "content", None) or raw_text, getattr(out, "reasoning", None))
    return {"prompt": g("prompt_tokens") or g("input_tokens"), "completion": g("completion_tokens") or g("output_tokens"),
            "thinking": think, "thinking_chars": len(t)}


def build_record(ctx: Context, item: Item, idx: int, seed: int, ep, out, parsed, scores, score_error,
                 raw_rel: str, reasoning_rel: str | None, key) -> dict:
    sc = ctx.scenarios[item.scenario]
    verdict = parsed.steps.get("verdict", {}) or {}
    fe = parsed.steps.get("fact_enumeration", {}) or {}
    opts = list((fe.get("options") or {}).keys()) if isinstance(fe.get("options"), dict) else []
    choice = verdict.get("choice")
    via = verdict.get("via")
    s = scores or {}
    return {
        "schema": SCHEMA_VERSION, "run_id": ctx.run_id, "item_id": item.id, "scenario": item.scenario,
        "family": sc.family, "arm": item.arm, "analogical_prompt": item.prompt, "mode": item.mode,
        "sample_idx": idx, "seed": seed, "served": ([key.served] if key.served else []),
        "scores": scores, "score_error": score_error,
        "parsed_choice": choice, "gold_choice": key.choice, "gold_acceptable": list(key.acceptable),
        "translated_choice": score_names.get(s, "translated_choice"),
        "choice_score": score_names.get(s, "choice"),
        "relation": verdict.get("relation"), "gold_relation": key.relation,
        "via": via, "gold_via": key.via,
        "model_options": opts, "n_model_options": len(opts),
        "model_choice_position": opts.index(choice) if choice in opts else None,
        "tokens": usage_tokens(out, out.raw_text), "seconds": getattr(out, "seconds", None),
        "finish_reason": getattr(out, "finish_reason", None),
        "format": format_report(parsed),
        "perturbation": perturbation_features(sc),
        "copy_baseline": copy_baseline(key, ctx.lib),
        "cues": gold_cues(key),
        "raw_path": raw_rel, "reasoning_path": reasoning_rel, "ts": time.time(),
    }


# ------------------------------------------------------------------ one sample
async def run_sample(ctx: Context, item: Item, idx: int, done: set | None = None) -> dict | None:
    """Run, score and persist one sample. Returns the record, or None when skipped (already in samples.jsonl)
    or failed (logged to errors.jsonl, retried on the next resume)."""
    if done is not None and (item.id, idx) in done:
        return None
    seed = sample_seed(ctx.run_seed, item, idx)
    sc = ctx.scenarios[item.scenario]
    try:
        async with ctx.sem:
            settings = ctx.settings(item, seed)
            ep = ctx.backend.build_episode(sc, item.arm, settings, ctx.lib)
            out = await ctx.backend.run(ep, settings)
        raw = out.raw_text
        parsed = parse_reply(raw, noref=item.arm == "none")
        key = sc.answer_key(item.arm)
        scores, score_error = None, None
        try:
            scores = await asyncio.to_thread(ctx.backend.score_reply, parsed, key, ep.served, ctx.judge)
        except Exception as e:                      # judge down etc.: keep the sample, rescore later
            score_error = f"{type(e).__name__}: {e}"
        stem = f"{safe_name(item.id)}__{idx}"
        raw_rel = f"raw/{stem}.txt"
        (ctx.run_dir / raw_rel).write_text(raw)
        reasoning_rel = None
        if getattr(out, "reasoning", None):
            reasoning_rel = f"raw/{stem}.reasoning.txt"
            (ctx.run_dir / reasoning_rel).write_text(out.reasoning)
        rec = build_record(ctx, item, idx, seed, ep, out, parsed, scores, score_error, raw_rel, reasoning_rel, key)
        await append_record(ctx, rec)
        if done is not None:
            done.add((item.id, idx))
        return rec
    except Exception as e:
        log_error(ctx, item, idx, e)
        return None


def write_manifest(ctx: Context, items, n_samples: int, extra: dict | None = None):
    m = {"run_id": ctx.run_id, "run_seed": ctx.run_seed, "n_samples": n_samples, "n_items": len(items),
         "total_samples": total_samples(items, n_samples), "modes": sorted({i.mode for i in items}),
         "arms": sorted({i.arm for i in items}), "scenarios": sorted({i.scenario for i in items}),
         "max_tokens": ctx.max_tokens, "settings_extra": ctx.settings_extra, "concurrency": ctx.concurrency,
         "started": time.strftime("%Y-%m-%dT%H:%M:%S"), **(extra or {})}
    try:
        from bench.models import role
        r = role("policy")
        m["policy"] = {"model": r.model, **r.params}
    except Exception as e:
        m["policy"] = f"unavailable: {e}"
    p = ctx.run_dir / "manifest.json"
    if p.exists():      # resume: keep the earlier manifest
        p.rename(ctx.run_dir / f"manifest.{time.strftime('%Y%m%dT%H%M%S')}.json")
    p.write_text(json.dumps(m, indent=2, default=str))
    return m


def rescore(ctx: Context, only_failed: bool = True) -> int:
    """Re-parse each saved raw completion and rescore (after a judge outage or a scorer change)."""
    recs = read_samples(ctx.samples_path)
    n = 0
    for r in recs:
        if only_failed and not r.get("score_error"):
            continue
        sc = ctx.scenarios[r["scenario"]]
        item = Item(r["scenario"], r["arm"], r["analogical_prompt"], r["mode"])
        settings = ctx.settings(item, r["seed"])
        ep = ctx.backend.build_episode(sc, item.arm, settings, ctx.lib)
        parsed = parse_reply((ctx.run_dir / r["raw_path"]).read_text(), noref=item.arm == "none")
        try:
            r["scores"] = ctx.backend.score_reply(parsed, sc.answer_key(item.arm), ep.served, ctx.judge)
            r["score_error"] = None
            r["choice_score"] = score_names.get(r["scores"], "choice")
            r["translated_choice"] = score_names.get(r["scores"], "translated_choice")
            n += 1
        except Exception as e:
            r["score_error"] = f"{type(e).__name__}: {e}"
    ctx.samples_path.write_text("".join(json.dumps(r, ensure_ascii=False, default=str) + "\n" for r in recs))
    return n
