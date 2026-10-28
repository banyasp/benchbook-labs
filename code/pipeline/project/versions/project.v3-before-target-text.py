"""project (code only, v2.4): PairRecord (+ trace record, accepted solve sample) -> SFT jsonl, RLVR jsonl, Inspect samples.

    data/exports/<version>/sft/sft.jsonl       train pairs: golden records (training.sft_data format) + chat `messages`
    data/exports/<version>/sft/dev.jsonl       dev pairs, same format (validation)
    data/exports/<version>/rl/rlvr.jsonl       train pairs: TRL rows (prompt, answer_key, served, gold, tables)
    data/exports/<version>/eval/inspect.jsonl  test / eval-only pairs: one Inspect sample per (pair, arm, card view, AR,
                                               equities cell) + G (answer_key); `cell` says which cell it is
    data/exports/<version>/manifest.json       counts, hashes, settings, provenance

Prompts come from `harness.pairs.build_pair_episode`, the one prompt builder: the SFT prompt is the PLAIN harness prompt
for the item (arm, card view, AR on/off; no worked examples, no rationalize hint; those are for sampling only).
**The mode is passed explicitly** (`mode=` has no default; the SFT export uses C): the documents are the assistant's
`<think>` text, closed before the verdict. Loss is on the reply only; for decoys the row carries `mask_after:
applicability` and `training.sft_data` sets labels to -100 after that document (the verdict stays in the text).

Eval cells (design §11, §13): per eval pair the CORE cell (pair's card view, AR on, E_d on) and, with
`eval_cells="all"`, the second-pass cells: `ar_off`, `thin` (eligible relevant pairs: follows/distinguished, full-view pair)
and `eq_off` (E_d off, arms none and relevant). Nothing is run here.
"""
from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from bench.schema.pipeline import EVAL_SPLITS, TRAIN_ARMS, PairRecord, sha256_obj, sha256_text
from harness.episode import ThinLeakError
from harness.pairs import build_pair_episode, trace_path
from harness.settings import HarnessSettings
from pipeline.render.util import make_step
from pipeline.solve.structure import GoldStructure
from pipeline.store import Store, write_json
from scorers.trl_adapter import served_column

GOLD_PROSE = {"why", "reasoning"}      # dropped from the RLVR gold record (applicability-why, reasoning prose)
THIN_RELATIONS = ("follows", "distinguished")
DEFAULT_WRITERS = ("granite-rs",)      # the teacher writer is not in the default export (design §10 step 5)
MODES = ("B", "C", "Cprime")


def _sample_file(store: Store, s) -> dict:
    return yaml.safe_load((store.root.parent / s.path.replace("pairs/", "store/pairs/", 1)).read_text())


def accepted_reply(pair: PairRecord, store: Store, k: int | None = None) -> tuple[int, str, dict] | None:
    """(k, reply text, sample file) of an accepted sample (or sample k). Among several: the sample file marked
    `selected`, else the best `score`, else the first. Reads `reply` (clean documents) or, failing that, `text`."""
    cands = []
    for i, s in enumerate(pair.solve, 1):
        if s.accepted and (k is None or k == i):
            f = _sample_file(store, s)
            # W1 (granite-rs) writes raw_text (= prefill + generated) and marks its pick `chosen: true`
            cands.append((f.get("k", i), f.get("reply") or f.get("text") or f.get("raw_text"), f))
    if not cands:
        return None
    sel = [c for c in cands if c[2].get("selected") or c[2].get("chosen") is True]
    if sel:
        return sel[0]
    scored = [c for c in cands if isinstance(c[2].get("score"), (int, float))]
    return max(scored, key=lambda c: c[2]["score"]) if scored else cands[0]


def clean_documents(reply: str) -> str:
    """The reply as plain consecutive documents, starting at fact_enumeration: no think opener, no </think> marker."""
    t = reply.replace("<think>", "").replace("</think>", "")
    i = t.find("kind: fact_enumeration")
    if i < 0:
        raise ValueError("reply has no fact_enumeration document")
    return t[i:].strip() + "\n"


def split_for_mode(reply: str, mode: str, prefill: str) -> tuple[str, str]:
    """-> (prefill, completion). B: documents are the reply. C/Cprime: documents inside <think>, closed before the
    verdict (the harness prefills `kind: fact_enumeration` in those modes)."""
    if mode == "B":
        return prefill, reply
    if mode in ("C", "Cprime"):
        reply = clean_documents(reply)
        i = reply.rfind("kind: verdict")
        if i < 0:
            raise ValueError("reply has no verdict document")
        think, verdict = reply[:i].rstrip() + "\n", reply[i:]
        first, _, rest = think.partition("\n")
        assert first.strip() == "kind: fact_enumeration", "reply must start with fact_enumeration"
        return prefill, rest + "</think>\n" + verdict
    raise ValueError(f"mode {mode!r} is not supported by project (A needs free thinking text)")


def rl_gold(g: GoldStructure) -> dict:
    """The gold record without reasoning prose and applicability-why: structure only (ids as the student sees them)."""
    p = g.pair
    pm = lambda m: [{"live": a, "case": b} for a, b in m]
    return {
        "pair": p.id, "intent": p.intent, "arm": p.arm, "gold_tier": p.gold_tier, "case": g.C.id, "scenario": g.T.id,
        "frame_map": p.frame.model_dump(), "options_map": dict(g.options_map),
        "fact_mapping": {"matched": pm(g.fact_map["matched"]), "corresponding": pm(g.fact_map["corresponding"]),
                         "live_only": g.fact_map["live_only"], "case_only": g.fact_map["case_only"]},
        "consideration_mapping": {"matched": pm(g.cons_map["matched"]), "corresponding": pm(g.cons_map["corresponding"]),
                                  "live_only": g.cons_map["live_only"], "case_only": g.cons_map["case_only"]},
        "governs": p.governs, "relation": p.relation, "via": g.via or None, "choice": g.choice,
        "acceptable": g.acceptable, "decisive": g.decisive,
        "touched": ({"item": g.case2served.get(p.touched.item), "condition": p.touched.condition}
                    if p.touched else None)}


def gold_for(pair: PairRecord, store: Store, C=None, T=None):
    """-> (GoldStructure, AnswerKey) for the pair, built by pipeline.solve.structure (which owns arm handling: `none` has
    no card, `revised` swaps in the revised card's A, `self` is the trace's own scenario). The trace's span map comes
    from the trace store when the pair does not carry one."""
    T = T or store.scenario(pair.trace_scenario)
    if pair.arm == "none":
        C = None
    else:
        C = C or store.scenario(pair.case_scenario or pair.trace_scenario)
    sm = None
    if pair.span_map is None and pair.trace_ref and store.has_trace(pair.trace_ref):
        sm = store.trace(pair.trace_ref).span_map
    g = GoldStructure.build(pair, C, T, span_map=sm)
    return g, g.answer_key()


def _ar_for(pair: PairRecord, default_share: float = 0.5) -> tuple[bool, str]:
    """AR prompt on/off for a training item. W-upstream assigns it (pair.ar_prompt); if it did not, a seeded hash of the
    pair id does (50%), and the row says so."""
    if pair.ar_prompt is not None:
        return pair.ar_prompt, "pair"
    h = int(sha256_text("ar|" + pair.id)[:8], 16) / 0xFFFFFFFF
    return h < default_share, "project-hash"


def pair_meta(pair: PairRecord, T, g: GoldStructure | None, *, mode: str, ar: bool, card_view: str,
              k: int | None = None) -> dict:
    meta = {"pair": pair.id, "arm": pair.arm, "card_view": card_view, "AR": ar, "ar_prompt": ar,
            "writer": pair.writer, "rationalized": "rationalized" in pair.tags, "d": pair.d,
            "realization": pair.realization, "tier": pair.gold_tier, "gold_tier": pair.gold_tier, "intent": pair.intent,
            "family": T.family, "split": pair.split, "relation": pair.relation, "mode": mode,
            "case": pair.case_scenario, "scenario": pair.trace_scenario, "domain": T.domain,
            "held_out": bool(T.held_out), "tags": list(pair.tags), "recommended_option": pair.recommended_option}
    if k is not None:
        meta["sample"] = k
    if g is not None:
        meta["verdict_position"] = g.option_ids.index(g.choice) + 1
        meta["n_options"] = len(g.option_ids)
        meta["verdict_move"] = T.case.options[g.live[g.choice].rpartition("/")[2]].move
    return meta


def sft_row(pair: PairRecord, store: Store, settings: HarnessSettings, k: int | None = None) -> dict | None:
    """One SFT row (golden record + messages), or None without a trace or an accepted sample."""
    got = accepted_reply(pair, store, k)
    if not got:
        return None
    k, reply, _ = got
    mode = settings.mode
    ar, ar_src = _ar_for(pair)
    ep = build_pair_episode(pair, store, settings, ar_prompt=ar)
    prefill, completion = split_for_mode(reply, mode, ep.prefill)
    T = store.scenario(pair.trace_scenario)
    g, _ = gold_for(pair, store, T=T)
    meta = pair_meta(pair, T, g, mode=mode, ar=ar, card_view=ep.meta["card_view"], k=k)
    meta["ar_source"] = ar_src
    row = {"id": f"{pair.id}:{k}:{mode}", "prompt_text": ep.prompt_text, "prefill": prefill, "completion": completion,
           "messages": ep.messages, "meta": meta}
    if pair.arm == "decoy":
        row["mask_after"] = "applicability"
    return row


def rl_row(pair: PairRecord, store: Store, settings: HarnessSettings) -> dict:
    T = store.scenario(pair.trace_scenario)
    ar, _ = _ar_for(pair)
    ep = build_pair_episode(pair, store, settings, ar_prompt=ar)
    g, key = gold_for(pair, store, T=T)
    meta = pair_meta(pair, T, g, mode=settings.mode, ar=ar, card_view=ep.meta["card_view"])
    kd = key.model_dump(by_alias=True, exclude_none=True)
    return {"id": pair.id, "prompt": ep.messages, "prompt_text": ep.prompt_text,
            "answer_key": json.dumps(kd, ensure_ascii=False), "served": served_column(ep.served),
            "gold": rl_gold(g), "tables": g.tables(), "meta": meta}


def eval_cells(pair: PairRecord, which: str = "all") -> list[dict]:
    """The eval cells of one pair. core = the pair's card view, AR on, E_d on. `which`: "core" | "all" (adds the
    second-pass cells: ar_off, thin, eq_off)."""
    view = pair.card_view
    cells = [{"cell": "core", "card_view": view, "ar": True, "equities": True}]
    if which == "all":
        if pair.arm != "none":
            cells.append({"cell": "ar_off", "card_view": view, "ar": False, "equities": True})
        if pair.arm == "relevant" and view == "full" and pair.relation in THIN_RELATIONS:
            cells.append({"cell": "thin", "card_view": "thin", "ar": True, "equities": True})
        if pair.arm in ("none", "relevant"):
            cells.append({"cell": "eq_off", "card_view": view, "ar": True, "equities": False})
    return cells


def eval_rows(pair: PairRecord, store: Store, settings: HarnessSettings, which: str = "all", *, index: dict | None = None,
              leaks: list | None = None) -> list[dict]:
    T = store.scenario(pair.trace_scenario)
    g, key = gold_for(pair, store, T=T)
    kd = key.model_dump(by_alias=True, exclude_none=True)
    out = []
    for c in eval_cells(pair, which):
        try:
            ep = build_pair_episode(pair, store, settings, equities=c["equities"], card_view=c["card_view"],
                                    ar_prompt=c["ar"])
        except ThinLeakError as e:                       # never serve a leaky thin card; say so in the manifest
            if leaks is not None:
                leaks.append({"pair": pair.id, "cell": c["cell"], "error": str(e)})
            continue
        meta = pair_meta(pair, T, g, mode=settings.mode, ar=c["ar"], card_view=c["card_view"])
        meta.update({"cell": c["cell"], "equities_on": c["equities"], "pair_card_view": pair.card_view,
                     **((index or {}).get(pair.id) or {}), "settings": ep.meta["settings"]})
        out.append({"id": f"{pair.id}:{c['card_view']}:ar{int(c['ar'])}:eq{int(c['equities'])}",
                    "input": ep.messages, "prompt_text": ep.prompt_text, "prefill": ep.prefill, "target": g.choice,
                    "metadata": {"answer_key": kd, "served": served_column(ep.served), **meta}})
    return out


def pair_index(pairs: list[PairRecord]) -> dict:
    """Per pair: the d of its trace's relevant pairs (where `none` rows are plotted) and its relevant restyle partner
    (same trace; for `revised` pairs, the minimal-pair comparison)."""
    rel_d = defaultdict(list)
    partner = {}
    for p in pairs:
        if p.arm == "relevant" and p.d is not None:
            rel_d[p.trace_scenario].append(p.d)
        if p.arm == "relevant" and p.intent == "restyle":
            partner.setdefault(p.trace_scenario, p.id)
    out = {}
    for p in pairs:
        d = rel_d.get(p.trace_scenario)
        out[p.id] = {"trace_relevant_d": (sum(d) / len(d)) if d else None,
                     "restyle_partner": partner.get(p.trace_scenario) if p.arm == "revised" else None}
    return out


def check_no_lineage_leak(train: list[PairRecord], evals: list[PairRecord], store: Store) -> list[str]:
    """Design §13.5: no eval trace (or served card) shares a family (lineage root) with a train/dev pair. -> offending eval pair ids."""
    cache: dict[str, str] = {}

    def fam(sid):
        if sid not in cache:
            cache[sid] = store.scenario(sid).family
        return cache[sid]

    def fams(p):
        return {fam(p.trace_scenario)} | ({fam(p.case_scenario)} if p.case_scenario else set())

    train_fam = set().union(*(fams(p) for p in train)) if train else set()
    return sorted(p.id for p in evals if fams(p) & train_fam)


def project_pair(pair: PairRecord, store: Store, equities=None, *, mode: str, settings: HarnessSettings | None = None,
                 k: int | None = None, eval_cells_: str = "core") -> dict | None:
    """-> {"sft", "rl", "eval": [rows], "warnings"} or None (no accepted sample). `mode` is required: no silent default.
    (`equities` kept for the old signature; the pair's own equities id is used.)"""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    settings = (settings or HarnessSettings()).with_(mode=mode)
    sft = sft_row(pair, store, settings, k)
    if sft is None:
        return None
    T = store.scenario(pair.trace_scenario)
    g, _ = gold_for(pair, store, T=T)
    return {"sft": sft, "rl": rl_row(pair, store, settings), "eval": eval_rows(pair, store, settings, eval_cells_),
            "warnings": g.warnings}


def _write_jsonl(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():                                   # keep every version
        v = path.parent / "versions"
        v.mkdir(exist_ok=True)
        path.rename(v / f"{path.stem}.{time.strftime('%Y%m%d-%H%M%S')}{path.suffix}")
    path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows))


def project_all(store: Store, version: str, pairs: list[PairRecord] | None = None, *, mode: str,
                settings: HarnessSettings | None = None, writers=DEFAULT_WRITERS, eval_cells_: str = "all",
                max_length: int | None = None) -> dict:
    """Export data/exports/<version>/{sft,rl,eval}. `mode` is required (no default)."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    pairs = pairs if pairs is not None else store.active_pairs()
    settings = (settings or HarnessSettings()).with_(mode=mode)
    out = store.exports / version
    idx = pair_index(pairs)
    train = [p for p in pairs if p.split == "train" and p.arm in TRAIN_ARMS]
    dev = [p for p in pairs if p.split == "dev" and p.arm in TRAIN_ARMS]
    evals = [p for p in pairs if p.split in EVAL_SPLITS]
    bad = check_no_lineage_leak(train + dev, evals, store)
    if bad:
        raise ValueError(f"eval pairs share a family with train/dev pairs: {bad[:10]} ({len(bad)} in all)")
    rows = {"sft": [], "dev": [], "rl": [], "eval": []}
    skipped, warns, hashes, leaks = [], {}, {}, []

    def inputs(p):
        return sha256_obj({"pair": p.dump(), "trace": json.loads(trace_path(p, store).read_text())["messages"]})

    for p in train + dev:
        try:
            if p.split == "train":
                rows["rl"].append(rl_row(p, store, settings))        # RL needs no written reply
            if writers and p.writer not in writers:
                skipped.append({"pair": p.id, "reason": f"writer {p.writer!r} not in {list(writers)}"})
                continue
            r = sft_row(p, store, settings)
        except ThinLeakError as e:
            leaks.append({"pair": p.id, "cell": "train", "error": str(e)})
            continue
        if r is None:
            skipped.append({"pair": p.id, "reason": "no accepted sample"})
            continue
        rows["sft" if p.split == "train" else "dev"].append(r)
        hashes[p.id] = inputs(p)
    for p in evals:
        rows["eval"] += eval_rows(p, store, settings, eval_cells_, index=idx, leaks=leaks)
        hashes[p.id] = inputs(p)
    if leaks:
        import sys
        print(f"WARNING: {len(leaks)} thin-view leak(s); those cells were NOT exported: {leaks[:3]}", file=sys.stderr)
    files = {"sft": out / "sft" / "sft.jsonl", "dev": out / "sft" / "dev.jsonl", "rl": out / "rl" / "rlvr.jsonl",
             "eval": out / "eval" / "inspect.jsonl"}
    for kind, path in files.items():
        _write_jsonl(path, rows[kind])
    length = None
    if max_length:
        from training import sft_data
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(settings.tokenizer)
        _, rej = sft_data.build_examples(rows["sft"], tok, False, max_length)
        length = sft_data.report_drops(rej, len(rows["sft"]), max_length)
        write_json(out / "sft" / "length_report.json", length)
    sf = rows["sft"]
    manifest = {
        "version": version, "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "mode": mode,
        "settings": settings.to_dict(), "writers": list(writers), "eval_cells": eval_cells_,
        "counts": {k: len(v) for k, v in rows.items()}, "pairs_total": len(pairs), "skipped": skipped,
        "thin_leaks": leaks, "max_length_report": length,
        "by_arm": dict(Counter(r["meta"]["arm"] for r in sf)),
        "by_card_view": dict(Counter(r["meta"]["card_view"] for r in sf)),
        "by_ar": dict(Counter(str(r["meta"]["AR"]) for r in sf)),
        "by_intent": dict(Counter(r["meta"]["intent"] for r in sf)),
        "by_relation": dict(Counter(r["meta"]["relation"] for r in sf)),
        "by_gold_tier": dict(Counter(r["meta"]["tier"] for r in sf)),
        "rationalized": sum(bool(r["meta"]["rationalized"]) for r in sf),
        "gold_move": dict(Counter(r["meta"]["verdict_move"] for r in sf)),
        "gold_position": dict(Counter(r["meta"]["verdict_position"] for r in sf)),
        "eval_by_cell": dict(Counter(r["metadata"]["cell"] for r in rows["eval"])),
        "eval_by_arm": dict(Counter(r["metadata"]["arm"] for r in rows["eval"] if r["metadata"]["cell"] == "core")),
        "input_sha256": hashes, "files": {k: str(v.relative_to(store.data)) for k, v in files.items()},
        "file_sha256": {k: sha256_text(v.read_text()) for k, v in files.items()},
        "provenance": make_step("project", "project", None, None, {"pairs": sha256_obj(hashes)}, {"mode": mode}).model_dump(),
    }
    write_json(out / "manifest.json", manifest)
    return manifest
