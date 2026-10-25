"""project (code only): PairRecord (+ trace, accepted solve sample) -> SFT jsonl, RLVR jsonl, Inspect samples.

    data/exports/<version>/sft/sft.jsonl      golden records (training.sft_data format) + chat `messages`
    data/exports/<version>/rl/rlvr.jsonl      TRL rows: prompt, answer_key (JSON str), served (JSON str), gold, tables
    data/exports/<version>/eval/inspect.jsonl Inspect samples: input messages, target, metadata (answer_key, served)
    data/exports/<version>/manifest.json      counts, input hashes, version, settings, provenance of the projection

SFT prompt = the harness's own Episode for the pair (same injection, equities, served card, format spec); the target is
the accepted teacher reply. Loss is on the target only: sft_data.tokenize_example masks everything in prompt_text.
Modes: B (default; documents as the reply), C / Cprime (documents inside <think>, </think> before the verdict). Mode A
needs free thinking text the teacher does not write and is refused.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import yaml

from bench.schema.pipeline import PairRecord, sha256_obj, sha256_text
from harness.settings import HarnessSettings
from pipeline.render.util import make_step
from pipeline.solve.episode import load_equities, student_episode
from pipeline.solve.structure import GoldStructure
from pipeline.store import Store, write_json
from scorers.trl_adapter import served_column

GOLD_PROSE = {"why", "reasoning"}      # dropped from the RLVR gold record (applicability-why, reasoning prose)


def accepted_reply(pair: PairRecord, store: Store, k: int | None = None) -> tuple[int, str, dict] | None:
    """(k, reply text, sample file) of the first accepted sample (or sample k)."""
    for i, s in enumerate(pair.solve, 1):
        if s.accepted and (k is None or k == i):
            f = yaml.safe_load((store.root.parent / s.path.replace("pairs/", "store/pairs/", 1)).read_text())
            return f["k"], f["reply"], f
    return None


def split_for_mode(reply: str, mode: str, prefill: str) -> tuple[str, str]:
    """-> (prefill, completion). B: documents are the reply. C/Cprime: documents inside <think>, closed before the
    verdict (the harness prefills `kind: fact_enumeration` in those modes)."""
    if mode == "B":
        return prefill, reply
    if mode in ("C", "Cprime"):
        i = reply.rfind("kind: verdict")
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
        "pair": p.id, "intent": p.intent, "gold_tier": p.gold_tier, "case": g.C.id, "scenario": g.T.id,
        "frame_map": p.frame.model_dump(), "options_map": dict(g.options_map),
        "fact_mapping": {"matched": pm(g.fact_map["matched"]), "corresponding": pm(g.fact_map["corresponding"]),
                         "live_only": g.fact_map["live_only"], "case_only": g.fact_map["case_only"]},
        "consideration_mapping": {"matched": pm(g.cons_map["matched"]), "corresponding": pm(g.cons_map["corresponding"]),
                                  "live_only": g.cons_map["live_only"], "case_only": g.cons_map["case_only"]},
        "governs": p.governs, "relation": p.relation, "via": g.via or None, "choice": g.choice,
        "acceptable": g.acceptable, "decisive": g.decisive,
        "touched": ({"item": g.case2served.get(p.touched.item), "condition": p.touched.condition}
                    if p.touched else None)}


def project_pair(pair: PairRecord, store: Store, equities=None, mode: str = "B", settings: HarnessSettings | None = None,
                 k: int | None = None) -> dict | None:
    """-> {"sft", "rl", "eval"} rows, or None when the pair has no trace or no accepted sample."""
    got = accepted_reply(pair, store, k) if pair.trace else None
    if not got:
        return None
    k, reply, _ = got
    C, T = store.scenario(pair.case_scenario), store.scenario(pair.trace_scenario)
    eq = load_equities(equities, T) if not hasattr(equities, "equities") else equities
    settings = (settings or HarnessSettings()).with_(mode=mode)
    ep = student_episode(pair, store, eq, settings, C=C)
    g = GoldStructure.build(pair, C, T)
    key = g.answer_key("relevant")
    prefill, completion = split_for_mode(reply, mode, ep.prefill)
    meta = {"pair": pair.id, "intent": pair.intent, "relation": pair.relation, "gold_tier": pair.gold_tier,
            "case": C.id, "scenario": T.id, "split": pair.split, "family": T.family, "mode": mode, "sample": k,
            "arm": "relevant", "verdict_position": g.option_ids.index(g.choice) + 1, "n_options": len(g.option_ids),
            "verdict_move": T.case.options[g.live[g.choice].rpartition("/")[2]].move,
            "teacher": next((s.model for s in pair.provenance.steps if s.id == "solve"), None)}
    sft = {"id": f"{pair.id}:{k}:{mode}", "prompt_text": ep.prompt_text, "prefill": prefill, "completion": completion,
           "messages": ep.messages, "meta": meta}
    served = served_column(ep.served)
    kd = key.model_dump(by_alias=True, exclude_none=True)
    rl = {"id": pair.id, "prompt": ep.messages, "answer_key": json.dumps(kd, ensure_ascii=False), "served": served,
          "gold": rl_gold(g), "tables": g.tables(), "meta": meta}
    ev = {"id": pair.id, "input": ep.messages, "target": g.choice,
          "metadata": {"answer_key": kd, "served": served, **meta, "settings": settings.to_dict()}}
    return {"sft": sft, "rl": rl, "eval": ev, "warnings": g.warnings, "episode": ep}


def project_all(store: Store, version: str, pairs: list[PairRecord] | None = None, equities=None, mode: str = "B",
                settings: HarnessSettings | None = None) -> dict:
    pairs = pairs if pairs is not None else store.pairs()
    out = store.exports / version
    rows = {"sft": [], "rl": [], "eval": []}
    skipped, warns, hashes = [], {}, {}
    for p in pairs:
        r = project_pair(p, store, equities, mode, settings)
        if r is None:
            skipped.append({"pair": p.id, "reason": "no trace" if not p.trace else "no accepted sample"})
            continue
        for kind in rows:
            rows[kind].append(r[kind])
        if r["warnings"]:
            warns[p.id] = r["warnings"]
        hashes[p.id] = sha256_obj({"pair": p.dump(), "trace": json.loads((store.pair_dir(p.id) / p.trace).read_text())["messages"]})
    files = {"sft": out / "sft" / "sft.jsonl", "rl": out / "rl" / "rlvr.jsonl", "eval": out / "eval" / "inspect.jsonl"}
    for kind, path in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():                                   # keep every version
            v = path.parent / "versions"
            v.mkdir(exist_ok=True)
            path.rename(v / f"{path.stem}.{time.strftime('%Y%m%d-%H%M%S')}{path.suffix}")
        path.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows[kind]))
    from collections import Counter
    manifest = {
        "version": version, "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "mode": mode,
        "settings": (settings or HarnessSettings()).with_(mode=mode).to_dict(),
        "counts": {k: len(v) for k, v in rows.items()}, "pairs_total": len(pairs), "skipped": skipped,
        "by_intent": dict(Counter(r["meta"]["intent"] for r in rows["sft"])),
        "by_relation": dict(Counter(r["meta"]["relation"] for r in rows["sft"])),
        "by_gold_tier": dict(Counter(r["meta"]["gold_tier"] for r in rows["sft"])),
        "gold_move": dict(Counter(r["meta"]["verdict_move"] for r in rows["sft"])),
        "gold_position": dict(Counter(r["meta"]["verdict_position"] for r in rows["sft"])),
        "input_sha256": hashes, "files": {k: str(v.relative_to(store.data)) for k, v in files.items()},
        "file_sha256": {k: sha256_text(v.read_text()) for k, v in files.items()},
        "gold_warnings": warns,
        "provenance": make_step("project", "project", None, None, {"pairs": sha256_obj(hashes)}, {"mode": mode}).model_dump(),
    }
    write_json(out / "manifest.json", manifest)
    return manifest
