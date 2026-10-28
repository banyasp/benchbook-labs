"""Balance (design §7.4). Everything is computed from PairRecord.choice, never from the trace scenario's own verdict.

- hand-up: gold move (ask / refuse), read from the Case options of the trace scenario, <= 1/3 per arm (and per train /
  eval group); source-gold arms are subsampled deterministically and the drops are reported.
- position: (a) first-mention rank of the gold option in tau (TraceRecord.span_map.options; only once rendered),
  (b) card-order position of the gold's counterpart on the served card. (b) is trimmed toward uniform by dropping from
  the over-represented positions (no re-ordered T copies exist any more); (a) is reported and can only be balanced by
  the sampler once traces exist.
- channels / recommendation: see channels.py (per trace, seeded, never conditioned on gold); the recommended-is-gold
  rate is reported per arm, not controlled.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from bench.schema.pipeline import PairRecord, Scenario
from pipeline.store import Store

from .arms import HANDUP, h, local


def group(rec: PairRecord) -> str:
    return "train" if rec.split == "train" else "eval"


def gold_move(rec: PairRecord, scen: dict[str, Scenario]) -> str:
    return scen[rec.trace_scenario].case.options[local(rec.choice)].move


def is_handup(rec: PairRecord, scen: dict[str, Scenario]) -> bool:
    return gold_move(rec, scen) in HANDUP


def card_position(rec: PairRecord, scen: dict[str, Scenario]) -> int | None:
    """1-based position, on the served card, of the gold option's counterpart (None: no counterpart / no card)."""
    c = rec.options_map.get(rec.choice)
    if not c or not rec.case_scenario or rec.case_scenario not in scen:
        return None
    return list(scen[rec.case_scenario].case.options).index(local(c)) + 1


def mention_rank(rec: PairRecord, store: Store | None) -> tuple[int, int] | None:
    """(rank, n_options) of the gold option among the options in order of first mention in tau; None before render."""
    if store is None or not store.has_trace(rec.trace_ref or rec.trace_scenario):
        return None
    sm = store.trace(rec.trace_ref or rec.trace_scenario).span_map
    first: dict[str, tuple[int, int]] = {}
    for o in sm.options:
        k = (o.message, o.start)
        if o.option not in first or k < first[o.option]:
            first[o.option] = k
    if rec.choice not in first:
        return None
    return sorted(first, key=first.get).index(rec.choice) + 1, len(first)


def cap_handups(recs: list[PairRecord], scen: dict[str, Scenario], seed: int, max_share: float = 1 / 3):
    """Per (arm, train/eval group): hand-up golds <= max_share of the group. -> (kept, dropped records)."""
    by = defaultdict(list)
    for r in recs:
        by[(r.arm, group(r))].append(r)
    kept, dropped = [], []
    for key, rs in sorted(by.items()):
        hu = sorted((r for r in rs if is_handup(r, scen)), key=lambda r: h(seed, "handup", r.case_scenario, r.trace_scenario, r.intent))
        other = [r for r in rs if r not in hu]
        allowed = int(len(other) * max_share / (1 - max_share) + 1e-9)
        kept += other + hu[:allowed]
        dropped += hu[allowed:]
    return kept, dropped


def trim_card_positions(recs: list[PairRecord], scen: dict[str, Scenario], seed: int, tolerance: float = 0.15):
    """Per (arm, group, n card options): drop from over-represented card positions until every position's share is
    <= 1/n + tolerance (deterministic order). Pairs without a counterpart (decoy, none) are untouched."""
    by = defaultdict(list)
    keep = []
    for r in recs:
        p = card_position(r, scen)
        if p is None:
            keep.append(r)
        else:
            by[(r.arm, group(r), len(scen[r.case_scenario].case.options))].append((p, r))
    dropped = []
    for (arm, g, n), rs in sorted(by.items()):
        rs.sort(key=lambda pr: h(seed, "pos", pr[1].case_scenario, pr[1].trace_scenario, pr[1].intent))
        cnt = Counter(p for p, _ in rs)
        total = len(rs)
        cap = None
        while True:
            top, c = max(cnt.items(), key=lambda kv: (kv[1], -kv[0]))
            if total <= 0 or c / total <= 1 / n + tolerance or c <= 1:
                break
            # drop one from the top position (the last in hash order), everything else stays
            idx = max(i for i, (p, _) in enumerate(rs) if p == top)
            dropped.append(rs.pop(idx)[1])
            cnt[top] -= 1
            total -= 1
        keep += [r for _, r in rs]
    return keep, dropped


def balance(recs: list[PairRecord], scen: dict[str, Scenario], seed: int, handup_share: float = 1 / 3,
            position_tolerance: float | None = 0.15):
    dropped = {"handup": [], "position": []}
    cur = recs
    for _ in range(4):
        cur, d1 = cap_handups(cur, scen, seed, handup_share)
        d2 = []
        if position_tolerance is not None:
            cur, d2 = trim_card_positions(cur, scen, seed, position_tolerance)
        dropped["handup"] += d1
        dropped["position"] += d2
        if not d1 and not d2:
            break
    return cur, dropped
