"""Discovery channels and the per-trace recommendation (design §7.4, §8.2; R50, R51).

Both are properties of the TRACE, not of any pair, and are never conditioned on which option is gold in any arm:
the draw sees only (seed, trace scenario id, the sorted option ids). Render (W5) calls these helpers so that the
numbers pair reports before rendering are the ones render writes into the TraceRecord.
"""
from __future__ import annotations

import hashlib
import random

from bench.schema.pipeline import CHANNELS, Scenario

RECOMMEND_SHARE = 0.5


def _rng(*parts) -> random.Random:
    return random.Random(int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:16], 16))


def _tid(trace_scenario) -> str:
    return trace_scenario.id if isinstance(trace_scenario, Scenario) else str(trace_scenario)


def _opts(trace_scenario, options) -> list[str]:
    """Global option ids, sorted so the input order (which may follow gold) can never matter."""
    if options is None:
        if not isinstance(trace_scenario, Scenario):
            raise ValueError("options are required when trace_scenario is an id")
        options = [trace_scenario.case.global_id(o) for o in trace_scenario.case.options]
    sid = _tid(trace_scenario)
    return sorted(o if "/" in o else f"{sid}/{o}" for o in options)


def assign_channels(trace_scenario, options=None, seed: int = 0) -> dict[str, str]:
    """Option (global T id) -> discovery channel: a seeded random permutation of CHANNELS per trace.
    With more options than channels the permutation is repeated (a fresh permutation per round)."""
    opts = _opts(trace_scenario, options)
    sid = _tid(trace_scenario)
    rng = _rng("channels", seed, sid)
    pool: list[str] = []
    while len(pool) < len(opts):
        perm = list(CHANNELS)
        rng.shuffle(perm)
        pool += perm
    shuffled = list(opts)
    rng.shuffle(shuffled)                       # which option gets which channel: random, not id order
    return {o: pool[i] for i, o in enumerate(shuffled)}


def assign_recommended(trace_scenario, options=None, seed: int = 0, share: float = RECOMMEND_SHARE) -> str | None:
    """About `share` of traces carry a recommendation; the option is uniform over ALL options (gold unseen)."""
    opts = _opts(trace_scenario, options)
    rng = _rng("recommend", seed, _tid(trace_scenario))
    if rng.random() >= share:
        return None
    return rng.choice(opts)


def assign_trace_plan(trace_scenario, options=None, seed: int = 0) -> dict:
    """What render needs in one call: {'channels': {...}, 'recommended_option': str | None}."""
    return {"channels": assign_channels(trace_scenario, options, seed),
            "recommended_option": assign_recommended(trace_scenario, options, seed)}
