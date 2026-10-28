"""Channel assignment and recommendation for a trace (design §7.4, R51).

W2 owns `pipeline.pair.channels.assign_channels(trace_scenario, options, seed)`. Until it exists this module supplies a
stand-in with the same signature; `resolve()` prefers W2's when importable. Both are deterministic, seeded per trace,
and never see the gold.

Stand-in contract:
    assign_channels(trace_scenario: str, options: list[str], seed: int) -> dict[str, Channel]
    pick_recommended(trace_scenario: str, options: list[str], seed: int) -> str | None   (~50% None, else uniform)
W2's real function may return the channels dict, or (channels, recommended_option), or an object with
`.channels` / `.recommended_option`; `resolve()` accepts all of those.
"""
from __future__ import annotations

import hashlib
import random

from bench.schema.pipeline import CHANNELS


def _rng(trace_scenario: str, seed: int, salt: str) -> random.Random:
    h = hashlib.sha256(f"{trace_scenario}|{seed}|{salt}".encode()).hexdigest()
    return random.Random(int(h[:16], 16))


def assign_channels(trace_scenario: str, options: list[str], seed: int) -> dict[str, str]:
    opts = sorted(options)                        # order-independent of the caller's (gold-dependent) ordering
    rng = _rng(trace_scenario, seed, "channels")
    pool: list[str] = []
    while len(pool) < len(opts):                  # distinct channels while they last, then another round
        r = list(CHANNELS)
        rng.shuffle(r)
        pool += r
    rng.shuffle(opts)
    return {o: pool[i] for i, o in enumerate(opts)}


def pick_recommended(trace_scenario: str, options: list[str], seed: int) -> str | None:
    rng = _rng(trace_scenario, seed, "recommended")
    if not options or rng.random() >= 0.5:
        return None
    return rng.choice(sorted(options))


def resolve(trace_scenario: str, options: list[str], seed: int) -> tuple[dict[str, str], str | None, str]:
    """-> (channels, recommended_option, source). Uses W2's pipeline.pair.channels when present."""
    try:
        from pipeline.pair import channels as w2          # type: ignore
        fn = getattr(w2, "assign_channels", None)
    except Exception:
        w2, fn = None, None
    if fn is None:
        return (assign_channels(trace_scenario, options, seed), pick_recommended(trace_scenario, options, seed),
                "render-standin")
    out = fn(trace_scenario, options, seed)
    rec, have_rec = None, False
    if isinstance(out, tuple):
        out, rec, have_rec = out[0], (out[1] if len(out) > 1 else None), len(out) > 1
    elif not isinstance(out, dict):
        rec, have_rec = getattr(out, "recommended_option", None), hasattr(out, "recommended_option")
        out = getattr(out, "channels")
    if not have_rec:
        pick = getattr(w2, "pick_recommended", None) or getattr(w2, "recommend", None) or pick_recommended
        rec = pick(trace_scenario, options, seed)
    return dict(out), rec, "pair.channels"
