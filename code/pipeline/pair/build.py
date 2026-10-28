"""pair (3c): store -> PairRecords for every arm (design §7), balanced, with card_view / AR assigned, distance and trace refs.

Candidates: arms.py. Order: candidates -> card_view / ar_prompt assignment (seeded, per train item, before sampling) ->
distance -> balance (hand-up cap per arm, card-position trim) -> ids -> write. Reordered T copies (2f) are retired;
legacy pair records stay on disk untouched and are reported apart.

    python -m pipeline.pair build [--decoys N] [--seed S] [--thin-share F] [--dry] | stats | gate-augmented | sync-traces | housekeeping-2f
"""
from __future__ import annotations

from collections import Counter, defaultdict

from bench.schema.pipeline import EVAL_SPLITS, PairRecord, Scenario
from bench.schema.pipeline import pair_id as _pair_id
from pipeline.ingest.splits import check_no_leak
from pipeline.solve.structure import effective_trace
from pipeline.store import Store, write_yaml

from . import arms as A
from . import balance as B
from .arms import Skips, h, local, now
from .channels import assign_recommended
from .distance import for_pair

AR_SHARE = 0.5
THIN_SHARE_DEFAULT = 0.0           # first SFT run; 0.3 later (config/pipeline.yaml: thin_share)
THIN_ARMS = ("relevant", "revised")


def pair_id(c: str, t: str, intent: str, arm: str | None = None, card_view: str = "full") -> str:
    """v2.4 id (design §7.1). Legacy 2f ids (hash of C|T|intent) are kept on existing records."""
    return _pair_id(c, t, intent, arm or ("decoy" if intent == "decoy" else "relevant"), card_view)


def config_thin_share() -> float:
    try:
        from pipeline.perturb.pconfig import get
        return float(get("thin_share", THIN_SHARE_DEFAULT))
    except Exception:
        return THIN_SHARE_DEFAULT


def _u(*parts) -> float:
    return int(h(*parts)[:10], 16) / 16 ** 10


def thin_eligible(r: PairRecord) -> bool:
    return r.split == "train" and r.arm in THIN_ARMS and r.relation in ("follows", "distinguished")


def assign_view_and_ar(r: PairRecord, seed: int, thin_share: float, ar_share: float = AR_SHARE) -> PairRecord:
    """Per training item, seeded, before sampling. Eval items: AR on, full card (both views are an eval-time switch)."""
    if r.split != "train":
        return r.model_copy(update={"card_view": "full", "ar_prompt": True})
    key = (r.case_scenario, r.trace_scenario, r.intent, r.arm)
    view = "thin" if thin_eligible(r) and _u(seed, "view", *key) < thin_share else "full"
    return r.model_copy(update={"card_view": view, "ar_prompt": _u(seed, "ar", *key) < ar_share})


def finalize(r: PairRecord, scen: dict[str, Scenario], store: Store, seed: int) -> PairRecord:
    T = scen[r.trace_scenario]
    C = scen.get(r.case_scenario) if r.case_scenario else None
    if r.arm == "none":
        r = r.model_copy(update={"d": None})
    else:
        r = for_pair(r, C, effective_trace(r, C, T) if C else T)
        if r.arm == "self":
            assert r.d == 0, (r.id, r.d)
    rec, src = None, "planned"
    tid = r.trace_ref or r.trace_scenario
    if store.has_trace(tid):
        rec, src = store.trace(tid).recommended_option, "trace"
    else:
        rec = assign_recommended(T, [T.case.global_id(o) for o in T.case.options], seed)
    r = r.model_copy(update={"recommended_option": rec, "trace_ref": tid,
                             "distance_features": {**r.distance_features, "recommended_source": src}})
    return r.model_copy(update={"id": pair_id(r.case_scenario, r.trace_scenario, r.intent, r.arm, r.card_view)})


# ------------------------------------------------------------------ report
def report_for(recs: list[PairRecord], scen: dict[str, Scenario], store: Store | None) -> dict:
    out = {}
    for arm in sorted({r.arm for r in recs}):
        for g in ("train", "eval"):
            rs = [r for r in recs if r.arm == arm and B.group(r) == g]
            if not rs:
                continue
            hu = [r for r in rs if B.is_handup(r, scen)]
            hu_i = defaultdict(lambda: [0, 0])
            for r in rs:
                hu_i[r.intent][1] += 1
                hu_i[r.intent][0] += B.is_handup(r, scen)
            cp = Counter(B.card_position(r, scen) for r in rs)
            ranks = [B.mention_rank(r, store) for r in rs]
            rk = Counter(x[0] for x in ranks if x)
            rec = [r for r in rs if r.recommended_option]
            src = Counter(r.distance_features.get("recommended_source", "trace") for r in rec)
            out[f"{arm}/{g}"] = {
                "n": len(rs), "by_intent": dict(Counter(r.intent for r in rs)), "by_tier": dict(Counter(r.gold_tier for r in rs)),
                "by_relation": dict(Counter(r.relation for r in rs)), "card_view": dict(Counter(r.card_view for r in rs)),
                "ar_prompt_on": sum(bool(r.ar_prompt) for r in rs),
                "handup": {"n": len(hu), "share": round(len(hu) / len(rs), 3),
                           "by_intent": {k: {"handup": v[0], "n": v[1]} for k, v in sorted(hu_i.items())}},
                "position_card_order": {str(k): v for k, v in sorted(cp.items(), key=lambda kv: (kv[0] is None, kv[0]))},
                "position_first_mention_rank": ({**{str(k): v for k, v in sorted(rk.items())},
                                                 "traces_rendered": sum(bool(x) for x in ranks), "of": len(rs)}
                                                if rk else "pending (no rendered traces)"),
                "recommended_is_gold": {"pairs_with_recommendation": len(rec),
                                        "rate": round(sum(r.recommended_option == r.choice for r in rec) / len(rec), 3) if rec else None,
                                        "source": dict(src)},
                "d_mean": round(sum(r.d for r in rs if r.d is not None) / max(1, sum(r.d is not None for r in rs)), 3),
                "tags": dict(Counter(t for r in rs for t in r.tags)),
            }
    return out


# ------------------------------------------------------------------ build
def build(store: Store, decoys: int = 2, seed: int = 0, write: bool = True, thin_share: float | None = None,
          position_tolerance: float | None = 0.15, check_leak: bool = True) -> dict:
    thin_share = config_thin_share() if thin_share is None else thin_share
    scen = {s.id: s for s in store.scenarios() if not A.is_retired_copy(s)}
    skips = Skips()
    partials = A.load_partials(store)
    cands = (A.derived(partials, scen, skips) + A.reverse_restyle(partials, scen, skips) + A.augmented(partials, scen, skips)
             + A.revised(partials, scen, skips) + A.decoys(scen, decoys, seed, skips) + A.self_pairs(scen, skips))
    eval_traces = {r.trace_scenario for r in cands if r.split in EVAL_SPLITS}
    cands += A.none_pairs(scen, eval_traces | {s.id for s in scen.values() if not s.lineage.parent and s.split in EVAL_SPLITS})
    cands = [assign_view_and_ar(r, seed, thin_share) for r in cands]
    before = report_for([finalize(r, scen, store, seed) for r in cands], scen, None)
    kept, dropped = B.balance(cands, scen, seed, position_tolerance=position_tolerance)
    final = [finalize(r, scen, store, seed) for r in kept]
    assert len({r.id for r in final}) == len(final), "duplicate pair ids"
    for r in final:
        C = scen.get(r.case_scenario)
        assert (C is None or C.split == scen[r.trace_scenario].split) and r.split == scen[r.trace_scenario].split, "pair crosses splits"
    written = 0
    if write:
        for r in final:
            ex = store.pair_dir(r.id) / "pair.yaml"
            if ex.exists():                                   # keep solve samples, writer, gate/rejection tags
                old = PairRecord.load(ex)
                keep_tags = {t for t in old.tags if t in ("rejected", "gate-passed", "gate-failed") or t.startswith("rationalized")}
                tags = (set(r.tags) - {"gate-pending"} if keep_tags & {"gate-passed", "gate-failed"} else set(r.tags)) | keep_tags
                r = r.model_copy(update={"solve": old.solve, "writer": old.writer, "span_map": old.span_map, "trace": old.trace,
                                         "tags": sorted(tags)})
            store.save_pair(r)
            written += 1
    rep = {"pairs": len(final), "candidates": len(cands), "written": written, "seed": seed, "thin_share": thin_share,
           "by_arm": dict(Counter(r.arm for r in final)), "by_intent": dict(Counter(r.intent for r in final)),
           "by_split": dict(Counter(r.split for r in final)),
           "dropped": {k: {"n": len(v), "pairs": [f"{r.arm}/{r.intent}: {r.case_scenario} -> {r.trace_scenario}" for r in v]}
                       for k, v in dropped.items()},
           "skipped": {"counts": skips.count(), "items": skips.items},
           "before_balance": before, "after_balance": report_for(final, scen, store)}
    if check_leak and write:
        rep["leak_violations"] = check_no_leak(store)
        assert not rep["leak_violations"], rep["leak_violations"]
    if write:
        write_yaml(store.root / "pair_build_report.yaml", rep)
    return rep


# ------------------------------------------------------------------ stats / maintenance
def is_current(r: PairRecord) -> bool:
    return r.id == pair_id(r.case_scenario, r.trace_scenario, r.intent, r.arm, r.card_view)


def stats(store: Store) -> dict:
    scen = {s.id: s for s in store.scenarios()}
    allp = store.pairs()
    cur = [r for r in allp if is_current(r) and "rejected" not in r.tags and r.trace_scenario in scen]
    rej = [r for r in allp if "rejected" in r.tags]
    return {"pairs_on_disk": len(allp), "current_v2.4": len(cur), "legacy_pre_v2.4": sum(not is_current(r) for r in allp),
            "rejected": {"n": len(rej), "ids": [r.id for r in rej]},
            "augmented_gate": dict(Counter(("passed" if "gate-passed" in r.tags else "failed" if "gate-failed" in r.tags else "pending")
                                           for r in allp if r.arm == "augmented")),
            "per_arm": report_for(cur, scen, store)}


def sync_traces(store: Store) -> dict:
    """After render: copy trace_ref / recommended_option from the trace store into the pairs (the planned value, from
    channels.assign_recommended, is replaced by what render actually wrote)."""
    n = changed = 0
    for p in store.pairs():
        tid = p.trace_ref or p.trace_scenario
        if not store.has_trace(tid):
            continue
        n += 1
        rec = store.trace(tid).recommended_option
        if p.recommended_option != rec or p.trace_ref != tid:
            store.save_pair(p.model_copy(update={"recommended_option": rec, "trace_ref": tid,
                                                 "distance_features": {**p.distance_features, "recommended_source": "trace"}}))
            changed += 1
    return {"pairs_with_trace": n, "updated": changed}


def housekeeping_2f(store: Store) -> dict:
    """2f example pairs (brief): reject P-1217d16660 (tag + reason; nothing deleted), re-tag P-7b3fe9966f as a
    paraphrase-realized flip, tag P-2c6540bbdd T2. Idempotent."""
    out = {}
    acts = {"P-1217d16660": ("rejected", "2f example pair rejected (BUILD-BRIEF-v2.4 2f housekeeping); kept on disk, skipped by exports", {}),
            "P-7b3fe9966f": (None, "re-tagged realization: paraphrase (BUILD-BRIEF-v2.4 2f housekeeping)", {"realization": "paraphrase"}),
            "P-2c6540bbdd": ("T2", "tagged T2 (BUILD-BRIEF-v2.4 2f housekeeping)", {})}
    for pid, (tag, why, upd) in acts.items():
        if not (store.pair_dir(pid) / "pair.yaml").exists():
            out[pid] = "missing"
            continue
        p = store.pair(pid)
        tags = set(p.tags) | ({tag} if tag else set())
        if tags == set(p.tags) and all(getattr(p, k) == v for k, v in upd.items()):
            out[pid] = "already done"
            continue
        p.provenance.step(id=f"housekeeping.{len(p.provenance.steps)}", operator="pair", notes=why, ts=now())
        store.save_pair(p.model_copy(update={"tags": sorted(tags), **upd}))
        out[pid] = why
    return out
