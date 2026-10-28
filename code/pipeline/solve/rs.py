"""rs: the SFT writer, rejection sampling Granite (design v2.4.1 section 10; BUILD-BRIEF-v2.4 W1).

    sampling prompt = the harness prompt for the item's arm, card view and AR setting (pipeline.solve.episode.student_episode,
                      harness mode C) + two worked examples prepended to the system message. No gold anywhere.
    round 1  n = 4 in ONE vLLM request (`n` per request, several requests in flight)
    round 2  4 more, only for items with no accepted sample
    round r  rationalize: items still without an accepted sample get one pass with a hint (gold choice text, relation,
             via in served ids); filtered the same way; the chosen sample is tagged `rationalized`
    filter   check_rs: cheapest first. free exact checks (parse, governs, relation, via) -> option alignment + choice ->
             only for survivors: fact / consideration alignment and bucket agreement. Every sub-score is logged per
             sample so thresholds can move without re-sampling.
    choose   one accepted sample per item, seeded random among those with the best score.

Reuses code/harness/ (build_episode, render, client._request/_finish: raw completions with the chat template, stop
markers). Nothing in code/harness/ was changed; the only private helpers used are client._request, _apost and _finish
(a public `n=` on run_episode/arun_episode would replace them).
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import random
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

from bench.schema import Case, EquitySet, parse_reply
from bench.schema.pipeline import TRAIN_ARMS, PairRecord, SolveSample, sha256_text
from harness import client
from harness.episode import Episode, render
from harness.settings import HarnessSettings
from pipeline.render.util import make_step, prompt_ref
from pipeline.store import Store, write_json, write_yaml
from scorers import alignment as A
from scorers import rows as R

from .check import _strings, placeholders
from .episode import load_equities, student_episode
from .structure import GoldStructure

HERE = Path(__file__).parent
PROMPTS = HERE / "prompts"
CONFIG_FILE = HERE / "rs.config.yaml"
EXAMPLE_FLIP = PROMPTS / "rs_example_flip.v1.yaml"
EXAMPLE_JRN_SITUATION = PROMPTS / "rs_example_journalist.situation.txt"
EXAMPLE_FLIP_SITUATION = PROMPTS / "rs_example_flip.situation.txt"
PDF_FIX = Path(__file__).resolve().parents[2] / "bench" / "fixtures" / "pdf_example"
WRITER = "granite-rs"
ROUNDS = ("1", "2", "r")


# ====================================================================== config
@dataclass
class Thresholds:
    fact_bucket_agreement: float = 0.7
    fact_recall: float = 0.6
    decisive_facts_exact: bool = True
    consideration_bucket_agreement: float = 0.7
    decisive_considerations: bool = True
    decisive_allow_extra: bool = True


@dataclass
class RSConfig:
    n_first: int = 4
    n_more: int = 4
    n_rationalize: int = 4
    rationalize: bool = True
    max_tokens: int = 8000
    mode: str = "C"
    role: str = "policy"
    seed: int = 0
    examples: bool = True
    concurrency: int = 16
    items_in_flight: int = 64
    check_workers: int = 8
    retries: int = 3
    require_strict: bool = True
    require_stop: bool = True
    thresholds: Thresholds = field(default_factory=Thresholds)

    @classmethod
    def load(cls, path=None, **overrides) -> "RSConfig":
        """rs.config.yaml defaults, then the keys of `path` (if given), then keyword overrides (None = not given)."""
        d = yaml.safe_load(CONFIG_FILE.read_text()) or {}
        if path:
            for k, v in (yaml.safe_load(Path(path).read_text()) or {}).items():
                if isinstance(v, dict) and isinstance(d.get(k), dict):
                    d[k] = {**d[k], **v}
                else:
                    d[k] = v
        for k, v in overrides.items():
            if v is not None:
                d[k] = v
        th = Thresholds(**(d.pop("thresholds", None) or {}))
        names = {f.name for f in dataclasses.fields(cls)}
        unknown = set(d) - names
        if unknown:
            raise ValueError(f"unknown rs config keys: {sorted(unknown)}")
        return cls(thresholds=th, **d)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


# ====================================================================== worked examples
def _doc_texts(text: str) -> list[str]:
    """Split a multi-document yaml text on `---`, drop comment lines and the PDF fixture's `note_2` workaround."""
    docs, cur = [], []
    for ln in text.splitlines():
        if ln.strip() == "---":
            docs.append(cur)
            cur = []
        elif not ln.lstrip().startswith("#") and not ln.startswith("note_2:"):
            cur.append(ln)
    docs.append(cur)
    return ["\n".join(d).strip("\n") for d in docs if any(x.strip() for x in d)]


def mode_c_layout(docs: list[str]) -> str:
    """Structure inside <think>, the verdict outside: the layout the model must produce in mode C."""
    return "<think>\n" + "\n---\n".join(docs[:-1]) + "\n</think>\n" + docs[-1] + "\n"


def example_replies() -> tuple[str, str]:
    """(journalist reply from the PDF fixture, converted v6 flip reply), both in mode C layout."""
    jr = _doc_texts((PDF_FIX / "journalist.reply.yaml").read_text())
    fl = _doc_texts(EXAMPLE_FLIP.read_text())
    return mode_c_layout(jr), mode_c_layout(fl)


def worked_examples() -> str:
    case = Case.load(PDF_FIX / "REF1.case.yaml").serve("REF1", "full")
    eq = EquitySet.model_validate(yaml.safe_load((PDF_FIX / "equities.yaml").read_text()))
    eqd = eq.served()
    for e in eqd["equities"]:
        e["gloss"] = re.sub(r"^\[NOT IN PDF LIST[^\]]*\]\s*", "", e["gloss"])
    j, f = example_replies()
    return (
        "<benchbook_worked_examples>\n"
        "Two worked examples of the reply you will have to write follow. They are about other scenarios than yours. Both reason "
        "from the same reference case, REF1, shown first. Your own equities, case, ids and facts come from the context after "
        "the examples; copy the layout and the method, never the wording or the content. Each example gives the situation in "
        "brief, then the complete reply: the documents inside <think>, then </think>, then the verdict document.\n"
        "<example_reference>\n<benchbook_equities>\n"
        + yaml.safe_dump(eqd, sort_keys=False, allow_unicode=True, width=200).strip()
        + "\n</benchbook_equities>\n<benchbook_case>\n" + case.yaml().strip() + "\n</benchbook_case>\n</example_reference>\n"
        "<example n=\"1\">\n<situation>\n" + EXAMPLE_JRN_SITUATION.read_text().strip() + "\n</situation>\n<reply>\n"
        + j.strip() + "\n</reply>\n</example>\n"
        "<example n=\"2\">\n<situation>\n" + EXAMPLE_FLIP_SITUATION.read_text().strip() + "\n</situation>\n<reply>\n"
        + f.strip() + "\n</reply>\n</example>\n"
        "End of the worked examples. Your own task follows.\n"
        "</benchbook_worked_examples>\n\n")


_EX_CACHE: dict = {}


def _examples_text() -> str:
    if "t" not in _EX_CACHE:
        _EX_CACHE["t"] = worked_examples()
    return _EX_CACHE["t"]


# ====================================================================== prompt building
def rs_settings(pair: PairRecord, cfg: RSConfig) -> HarnessSettings:
    return HarnessSettings(mode=cfg.mode, analogical_prompt=bool(pair.ar_prompt), max_tokens=cfg.max_tokens)


def _rerender(ep: Episode, messages: list[dict], settings: HarnessSettings) -> Episode:
    gen, opener, prefill = render(messages, ep.tools, settings)
    return dataclasses.replace(ep, messages=messages, prompt_text=gen + prefill[len(opener):], prefill=prefill,
                               generation_prompt=gen, opener=opener)


def with_examples(ep: Episode, settings: HarnessSettings) -> Episode:
    msgs = [dict(m) for m in ep.messages]
    assert msgs[0]["role"] == "system"
    msgs[0]["content"] = _examples_text() + msgs[0]["content"]
    return _rerender(ep, msgs, settings)


def rationalize_hint(g: GoldStructure) -> str:
    """The hint for the rationalize pass: gold choice (by its text: option ids are the model's own), relation, via
    (served ids). Never part of the plain sampling prompt, never part of the SFT prompt."""
    p = g.pair
    opt = g.T.case.options[g.live[g.choice].rpartition("/")[2]].do
    lines = [f"- verdict.choice is the option: \"{opt}\" (use the LIVE id you gave that option)",
             f"- verdict.relation is {p.relation}", f"- applicability.governs is {str(p.governs).lower()}"]
    if g.via:
        lines.append(f"- verdict.via is [{', '.join(g.via)}]")
    return ("<benchbook_hint>\nThe conclusion for this reply is already settled:\n" + "\n".join(lines)
            + "\nWrite the documents as your own honest analysis of the trace and the case, the way a careful analyst who "
              "reached this conclusion would write them: map the facts and considerations as you actually find them. Do not "
              "mention this note or say that the conclusion was given.\n</benchbook_hint>")


def with_hint(ep: Episode, settings: HarnessSettings, hint: str) -> Episode:
    msgs = [dict(m) for m in ep.messages]
    msgs[-1]["content"] = msgs[-1]["content"].rstrip() + "\n" + hint
    return _rerender(ep, msgs, settings)


@dataclass
class Prepared:
    pair: PairRecord
    g: GoldStructure
    ep: Episode                   # plain sampling prompt (examples included, no hint)
    settings: HarnessSettings
    base_ep: Episode              # the plain harness prompt (what SFT will use)


def prepare(pair: PairRecord, store: Store, cfg: RSConfig, equities=None) -> Prepared:
    if pair.arm not in TRAIN_ARMS:
        raise ValueError(f"{pair.id}: arm {pair.arm} is eval only; RS runs on {TRAIN_ARMS}")
    g = GoldStructure.from_store(store, pair)
    settings = rs_settings(pair, cfg)
    eq = equities if hasattr(equities, "equities") else (load_equities(equities, g.T) if equities else None)
    base = student_episode(pair, store, eq, settings, C=g.C)
    ep = with_examples(base, settings) if cfg.examples else base
    return Prepared(pair, g, ep, settings, base)


# ====================================================================== the filter
@dataclass
class RSCheck:
    accepted: bool
    reasons: list[str]
    stage: str                     # parse | exact | choice | structure | accepted
    sub: dict
    score: float


HINT_LEAK = re.compile(r"\b(hint|the note (says|above)|(conclusion|answer) (was|is) (given|settled)|i was (told|instructed|given))\b", re.I)


def _positions(gold_map, ids: list[str]) -> dict:
    out = {}
    for b in ("matched", "corresponding"):
        for p in getattr(gold_map, b):
            out.setdefault(p.live, (b, p.case))
    for x in gold_map.live_only:
        out.setdefault(x, ("live_only", None))
    return {i: out[i] for i in ids if i in out}


def _agent_positions(agent: dict) -> dict:
    out = {}
    for b in ("matched", "corresponding"):
        for live, case in sorted(agent[b], key=str):
            out.setdefault(live, (b, case))
    for x in agent["live_only"]:
        out.setdefault(x, ("live_only", None))
    return out


def bucket_agreement(gold_map, gold_ids: list[str], agent: dict) -> dict:
    """Agreeing gold items / ALL gold items. A gold live item agrees when the agent's aligned counterpart sits in the
    same bucket (and, for matched / corresponding, with the same case partner); an unaligned one disagrees. A gold
    case_only item agrees when the agent lists it in case_only."""
    gp, ap = _positions(gold_map, gold_ids), _agent_positions(agent)
    live_bad = [i for i in gold_ids if ap.get(i) != gp.get(i)]
    case_only = list(gold_map.case_only)
    case_bad = [c for c in case_only if c not in agent["case_only"]]
    total = len(gold_ids) + len(case_only)
    ok = total - len(live_bad) - len(case_bad)
    return {"agreement": (ok / total) if total else 1.0, "agree": ok, "total": total,
            "disagree_live": live_bad, "disagree_case_only": case_bad}


def check_rs(raw_text: str, g: GoldStructure, judge, cfg: RSConfig | None = None, finish_reason: str | None = "stop",
             hinted: bool = False) -> RSCheck:
    cfg = cfg or RSConfig.load()
    th, pair = cfg.thresholds, g.pair
    sub: dict = {"finish_reason": finish_reason, "arm": pair.arm, "gold_tier": pair.gold_tier}
    parsed = parse_reply(raw_text)
    reasons: list[str] = []
    # ---- stage parse (no judge)
    if cfg.require_stop and finish_reason == "length":
        reasons.append("truncated: hit max_tokens")
    sub["strict_ok"] = parsed.strict_ok
    if cfg.require_strict and not parsed.strict_ok:
        why = []
        if parsed.missing:
            why.append(f"missing {parsed.missing}")
        why += [f"{k}: {v[:80]}" for k, v in parsed.errors.items() if k in parsed.required() and k not in parsed.missing]
        if any(parsed.repairs.values()):
            why.append("repairs")
        if parsed.unknown_kinds:
            why.append(f"unknown kinds {parsed.unknown_kinds}")
        reasons.append("parse: " + "; ".join(why))
    copied = sorted({x.strip()[:50] for x in _strings(list(parsed.steps.values())) if x.strip().lower() in placeholders()})
    if copied:
        reasons.append(f"placeholder text copied from the format spec: {copied}")
    if hinted:
        leak = sorted({m.group(0).lower() for x in _strings(list(parsed.steps.values())) for m in HINT_LEAK.finditer(x)})
        sub["hint_leak"] = leak
        if leak:
            reasons.append(f"hint leaked into the text: {leak}")
    if reasons:
        return RSCheck(False, reasons, "parse", sub, 0.0)
    key = g.answer_key()
    ctx = R.ScoringContext(parsed, key, [g.served], judge)
    # ---- stage exact, free checks first
    ex = {"governs": R.applicability_governs(ctx), "relation": R.verdict_relation(ctx)}
    agent_via = {ctx.to_global(v) for v in R._agent_via(ctx)}
    ex["via"] = int(agent_via == set(pair.via or []))
    sub.update(ex)
    for k, v in ex.items():
        if not v:
            reasons.append(f"{k} differs from gold")
    if reasons:
        return RSCheck(False, reasons, "exact", sub, 0.0)
    if pair.arm == "decoy":                           # governs and relation only
        sub["decoy_only"] = True
        return RSCheck(True, [], "accepted", sub, 1.0)
    # ---- option alignment (first judge calls) and the choice
    sub["choice"] = R.verdict_choice(ctx, gate=False)
    sub["choice_how"] = ctx.notes.get("choice")
    sub["options_aligned"] = {a: g_ for a, g_ in ctx.option_al.translation.items()}
    if not sub["choice"]:
        return RSCheck(False, ["choice differs from gold"], "choice", sub, 0.0)
    # ---- stage structure, survivors only
    try:
        fa = ctx.fact_al
        agent_f = R._translate_mapping(ctx, ctx.step("fact_mapping"), ctx.fact_tr)
        fb = bucket_agreement(key.fact_mapping, [f.id for f in key.facts], agent_f)
        wts = {f.id: f.weight for f in key.facts}
        tot = sum(wts.values()) or 1.0
        present = set(fa.present)
        recall = sum(w for i, w in wts.items() if i in present) / tot
        dec_facts = [i for i, w in wts.items() if w > 1.0]
        dec_bad = [i for i in dec_facts if i in fb["disagree_live"]]
        sub["facts"] = {**fb, "recall": recall, "found": len(fa.found), "conflated": len(fa.conflated),
                        "absent": list(fa.absent), "extraneous": len(fa.extraneous), "duplicate": len(fa.duplicate),
                        "decisive_wrong": dec_bad, "n_agent": len(fa.gen_ids), "n_gold": len(fa.gold_ids)}
        if fb["agreement"] < th.fact_bucket_agreement:
            reasons.append(f"fact bucket agreement {fb['agreement']:.2f} < {th.fact_bucket_agreement}")
        if recall < th.fact_recall:
            reasons.append(f"fact recall {recall:.2f} < {th.fact_recall}")
        if th.decisive_facts_exact and dec_bad:
            reasons.append(f"decisive facts in the wrong bucket: {dec_bad}")
        scores = [fb["agreement"], recall]
        if pair.gold_tier == "model-solved":
            sub["consideration_checks"] = "skipped: model-solved pair (design 9.1)"
        else:
            agent_c = R._translate_mapping(ctx, ctx.step("consideration_mapping"), ctx.cons_tr)
            cb = bucket_agreement(key.consideration_mapping, [c.id for c in key.considerations], agent_c)
            dc = R.verdict_decisive(ctx)
            sub["considerations"] = {**cb, "decisive": ({k: dc[k] for k in ("key_only", "both", "agent_only")} if dc else None),
                                     "n_agent": len(ctx.cons_al.gen_ids), "n_gold": len(ctx.cons_al.gold_ids),
                                     "absent": list(ctx.cons_al.absent)}
            if cb["agreement"] < th.consideration_bucket_agreement:
                reasons.append(f"consideration bucket agreement {cb['agreement']:.2f} < {th.consideration_bucket_agreement}")
            if th.decisive_considerations and dc is not None:
                if dc["key_only"] or (dc["agent_only"] and not th.decisive_allow_extra):
                    reasons.append(f"decisive considerations differ (missing {dc['key_only']}, extra {dc['agent_only']})")
            scores.append(cb["agreement"])
        score = sum(scores) / len(scores)
    except (KeyError, TypeError, ValueError, AttributeError, IndexError) as e:
        sub["check_error"] = f"{type(e).__name__}: {e}"
        return RSCheck(False, [f"check error: {e}"], "structure", sub, 0.0)
    sub["score"] = score
    return RSCheck(not reasons, reasons, "accepted" if not reasons else "structure", sub, score)


# ====================================================================== sampling
async def asample(ep: Episode, settings: HarnessSettings, n: int, seed: int | None, role: str = "policy",
                  retries: int = 3, timeout: float = 3600) -> list[client.Completion]:
    """One /v1/completions request with `n` choices (prefix caching shares the prompt) -> n Completions."""
    cfg, url, payload = client._request(ep.prompt_text, settings, role, seed)
    payload["n"] = n
    t0 = time.time()
    for attempt in range(retries + 1):
        try:
            resp = await client._apost(url, payload, timeout)
            break
        except Exception as e:                       # transient transport / server errors
            if attempt == retries:
                raise
            await asyncio.sleep(2 ** attempt)
    outs = []
    for i, ch in enumerate(resp["choices"]):
        r = {**resp, "choices": [ch]}
        if i:
            r["usage"] = {}
        outs.append(client._finish(r, ep.prefill, t0, cfg, payload, ep.meta, "rs"))
    return outs


def _seed(cfg: RSConfig, pair_id: str, rnd: str) -> int:
    return int(sha256_text(f"{cfg.seed}|{pair_id}|{rnd}")[:8], 16)


# ====================================================================== one item
@dataclass
class ItemResult:
    pair_id: str
    samples: list[dict]
    chosen: dict | None
    error: str | None = None


def choose(samples: list[dict], seed: int, pair_id: str) -> dict | None:
    """One accepted sample, random (seeded) among those with the best score. Never mixes rationalized with plain:
    rationalized samples exist only when no plain sample was accepted."""
    acc = [s for s in samples if s["accepted"]]
    if not acc:
        return None
    best = max(s["score"] for s in acc)
    top = sorted((s for s in acc if s["score"] >= best - 1e-9), key=lambda s: s["name"])
    return random.Random(sha256_text(f"{seed}|{pair_id}|choose")).choice(top)


async def process_item(pair: PairRecord, store: Store, judge, cfg: RSConfig, sem: asyncio.Semaphore, equities=None,
                       sampler: Callable | None = None, rounds_override: tuple | None = None) -> ItemResult:
    sampler = sampler or asample
    prep = await asyncio.to_thread(prepare, pair, store, cfg, equities)
    g = prep.g
    samples: list[dict] = []
    if rounds_override and "1" not in rounds_override:        # e.g. rationalize-only: keep the earlier rounds' samples
        for f in sorted((store.pair_dir(pair.id) / "solve").glob("rs-[12]-*.yaml")):
            samples.append({**yaml.safe_load(f.read_text()), "name": f.stem})

    async def run_round(rnd: str, ep: Episode, n: int, hinted: bool):
        async with sem:
            comps = await sampler(ep, prep.settings, n, _seed(cfg, pair.id, rnd), cfg.role, cfg.retries)
        checks = await asyncio.gather(*[asyncio.to_thread(check_rs, c.raw_text, g, judge, cfg, c.finish_reason, hinted)
                                        for c in comps])
        for k, (c, ck) in enumerate(zip(comps, checks), 1):
            samples.append({"name": f"rs-{rnd}-{k}", "round": rnd, "k": k, "hinted": hinted, "rationalized": hinted,
                            "accepted": ck.accepted, "reasons": ck.reasons, "stage": ck.stage, "subscores": ck.sub,
                            "score": ck.score, "finish_reason": c.finish_reason, "usage": c.usage, "seconds": c.seconds,
                            "seed": _seed(cfg, pair.id, rnd), "raw_text": c.raw_text, "generated": c.generated,
                            "prompt_sha256": sha256_text(ep.prompt_text)})

    rounds = rounds_override or ROUNDS
    if "1" in rounds and cfg.n_first:
        await run_round("1", prep.ep, cfg.n_first, False)
    if "2" in rounds and cfg.n_more and not any(s["accepted"] for s in samples):
        await run_round("2", prep.ep, cfg.n_more, False)
    if "r" in rounds and cfg.rationalize and cfg.n_rationalize and not any(s["accepted"] for s in samples):
        await run_round("r", await asyncio.to_thread(with_hint, prep.ep, prep.settings, rationalize_hint(g)),
                        cfg.n_rationalize, True)
    chosen = choose(samples, cfg.seed, pair.id)
    return ItemResult(pair.id, samples, chosen)


# ====================================================================== persistence
def persist(res: ItemResult, store: Store, cfg: RSConfig) -> PairRecord:
    """Sample files solve/rs-<round>-<k>.yaml, solve/rs.summary.yaml, and the pair record (solve list, writer, tags)."""
    pair = store.pair(res.pair_id)                       # fresh: other agents may have touched the record
    pdir = store.pair_dir(pair.id)
    ps = prompt_ref(EXAMPLE_FLIP)
    inputs = {"equities": pair.equities, "case": pair.case_scenario, "trace": pair.trace_ref or pair.trace_scenario}
    entries = []
    for s in res.samples:
        rel = f"solve/{s['name']}.yaml"
        body = {k: v for k, v in s.items() if k != "name"}
        body.update({"writer": WRITER, "chosen": bool(res.chosen and res.chosen["name"] == s["name"]),
                     "tags": ["rationalized"] if s["rationalized"] else []})
        write_yaml(pdir / rel, body)
        entries.append(SolveSample(path=f"pairs/{pair.id}/{rel}", accepted=s["accepted"], reasons=s["reasons"]))
    pair.solve = [x for x in pair.solve if "/rs-" not in x.path] + entries
    summary = {"writer": WRITER, "chosen": res.chosen["name"] if res.chosen else None,
               "rationalized": bool(res.chosen and res.chosen["rationalized"]),
               "score": res.chosen["score"] if res.chosen else None,
               "samples": len(res.samples), "accepted": sum(s["accepted"] for s in res.samples),
               "accepted_by_round": {r: sum(s["accepted"] for s in res.samples if s["round"] == r) for r in ROUNDS},
               "config": cfg.to_dict()}
    write_yaml(pdir / "solve/rs.summary.yaml", summary)
    if res.chosen:
        pair.writer = WRITER
        tags = [t for t in pair.tags if t != "rationalized"]
        pair.tags = tags + (["rationalized"] if res.chosen["rationalized"] else [])
    elif pair.writer == WRITER:
        pair.writer = None
        pair.tags = [t for t in pair.tags if t != "rationalized"]
    pair.provenance.steps = [x for x in pair.provenance.steps if not x.id.startswith("solve")]
    pair.provenance.step(**make_step("solve.rs", "solve", cfg.role, ps, inputs,
                                     {"writer": WRITER, "mode": cfg.mode, "n_first": cfg.n_first, "n_more": cfg.n_more,
                                      "n_rationalize": cfg.n_rationalize, "max_tokens": cfg.max_tokens, "seed": cfg.seed,
                                      "accepted": summary["accepted"], "chosen": summary["chosen"],
                                      "thresholds": dataclasses.asdict(cfg.thresholds)}).model_dump())
    pair.provenance.fields["solve"] = "solve.rs"
    store.save_pair(pair)
    return pair


def is_done(pair: PairRecord, store: Store) -> bool:
    return (store.pair_dir(pair.id) / "solve" / "rs.summary.yaml").exists()


def eligible(pair: PairRecord, split: str | None = "train") -> str | None:
    """None if RS can run on this pair, else the reason it cannot."""
    if pair.arm not in TRAIN_ARMS:
        return f"arm {pair.arm} is eval only"
    if split and pair.split != split:
        return f"split {pair.split}"
    if not (pair.trace_ref or pair.trace):
        return "no trace (run render)"
    if not pair.case_scenario:
        return "no card"
    return None


# ====================================================================== batch driver
async def _run(pairs: list[PairRecord], store: Store, judge, cfg: RSConfig, equities, sampler, log, rounds) -> list[ItemResult]:
    loop = asyncio.get_running_loop()
    loop.set_default_executor(ThreadPoolExecutor(max_workers=max(cfg.check_workers, 4)))
    sem, gate = asyncio.Semaphore(cfg.concurrency), asyncio.Semaphore(cfg.items_in_flight)
    out: list[ItemResult] = []

    async def one(p):
        async with gate:
            try:
                r = await process_item(p, store, judge, cfg, sem, equities, sampler, rounds)
                await asyncio.to_thread(persist, r, store, cfg)
                log(f"{p.id} [{p.arm}/{p.intent}/{p.card_view}]: {sum(s['accepted'] for s in r.samples)}/{len(r.samples)} accepted"
                    + (" (rationalized)" if r.chosen and r.chosen["rationalized"] else ""))
            except Exception as e:                    # one bad item must not sink the batch
                r = ItemResult(p.id, [], None, f"{type(e).__name__}: {e}")
                log(f"{p.id}: ERROR {r.error}")
            out.append(r)

    await asyncio.gather(*[one(p) for p in pairs])
    return out


def run_rs(pairs: list[PairRecord], store: Store, judge, cfg: RSConfig | None = None, equities=None,
           sampler: Callable | None = None, log: Callable = lambda m: None, rounds: tuple | None = None) -> list[ItemResult]:
    """Sample, filter, rationalize, choose and persist, for many items at once (vLLM `n` per request, several requests in
    flight). `sampler(ep, settings, n, seed, role, retries) -> list[Completion]` is injectable for tests."""
    cfg = cfg or RSConfig.load()
    return asyncio.run(_run(pairs, store, judge, cfg, equities, sampler, log, rounds))


# ====================================================================== acceptance
def acceptance(store: Store, cfg: RSConfig | None = None) -> dict:
    """Acceptance per arm / intent / family / tier / card view, from the sample files of every pair with an rs.summary."""
    dims = ("arm", "intent", "family", "gold_tier", "card_view")
    agg: dict = {d: defaultdict(lambda: _blank()) for d in dims}
    agg["overall"] = {"all": _blank()}
    for p in store.pairs():
        sp = store.pair_dir(p.id) / "solve" / "rs.summary.yaml"
        if not sp.exists():
            continue
        summ = yaml.safe_load(sp.read_text())
        try:
            family = store.scenario(p.trace_scenario).family
        except KeyError:
            family = "?"
        files = [yaml.safe_load(f.read_text()) for f in sorted((store.pair_dir(p.id) / "solve").glob("rs-*.yaml"))
                 if f.name != "rs.summary.yaml"]
        keys = {"arm": p.arm, "intent": p.intent, "family": family, "gold_tier": p.gold_tier, "card_view": p.card_view}
        buckets = [agg["overall"]["all"]] + [agg[d][keys[d]] for d in dims]
        for b in buckets:
            b["pairs"] += 1
            b["pairs_with_accept"] += bool(summ["chosen"])
            b["pairs_rationalized"] += bool(summ["rationalized"])
            b["pairs_accepted_plain"] += bool(summ["chosen"] and not summ["rationalized"])
            for r in ROUNDS:
                b["pairs_accepted_in_round"][r] += bool(summ["accepted_by_round"].get(r))
            for s in files:
                b["samples"] += 1
                b["accepted"] += bool(s["accepted"])
                if not s["accepted"]:
                    b["rejected_at"][s["stage"]] += 1
                    for r_ in s["reasons"][:1]:
                        b["reasons"][re.split(r"[:\d(\[]", r_)[0].strip()[:48]] += 1
    out = {"writer": WRITER, "thresholds": dataclasses.asdict((cfg or RSConfig.load()).thresholds),
           "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    for d, m in agg.items():
        out[d] = {k: _fin(v) for k, v in m.items()}
    return out


def _blank() -> dict:
    return {"pairs": 0, "pairs_with_accept": 0, "pairs_accepted_plain": 0, "pairs_rationalized": 0,
            "pairs_accepted_in_round": defaultdict(int), "samples": 0, "accepted": 0,
            "rejected_at": defaultdict(int), "reasons": defaultdict(int)}


def _fin(b: dict) -> dict:
    d = {k: (dict(v) if isinstance(v, defaultdict) else v) for k, v in b.items()}
    d["sample_rate"] = round(b["accepted"] / b["samples"], 3) if b["samples"] else None
    d["pair_rate_plain"] = round(b["pairs_accepted_plain"] / b["pairs"], 3) if b["pairs"] else None
    d["pair_rate_with_rationalized"] = round(b["pairs_with_accept"] / b["pairs"], 3) if b["pairs"] else None
    return d


def write_acceptance(store: Store, cfg: RSConfig | None = None) -> dict:
    rep = acceptance(store, cfg)
    write_json(store.root / "solve.acceptance.json", rep)
    return rep
