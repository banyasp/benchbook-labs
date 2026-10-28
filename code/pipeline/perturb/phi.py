"""Regularize X' flip conditions Φ (R35, R53) so a flipped scenario served as a card (augmented arm) doesn't look flipped.

- same `would_change` count as X (a vacuous item was dropped; the model must add non-vacuous authored ones, tagged authored);
- the touched consideration's weight is not systematically `weak`: it must come from the weights untouched considerations carry;
- would_change order shuffled (seeded) and ids renumbered flip1..n so neither position nor id order marks the new/back item;
- a back-flip item exists whose `then` is X's choice.
"""
from __future__ import annotations

import random

from bench.schema.common import PROSE_REF


def check_touched_weight(d: dict, tc: str, c_weight: str) -> None:
    t = next((c for c in d["considerations"] if c["id"] == tc), None)
    if t is None:
        return
    if t["weight"] == "weak" and c_weight != "weak":
        raise ValueError(f"{tc} was `{c_weight}` in the parent: do not weaken it to `weak` (a weak touched consideration marks a "
                         "flip). Keep its weight like the untouched considerations.")
    others = {c["weight"] for c in d["considerations"] if c["id"] != tc}
    if others and t["weight"] not in others | {c_weight}:
        raise ValueError(f"{tc} weight `{t['weight']}` must be one the untouched considerations carry ({sorted(others)}) or its original `{c_weight}`")


def check_count(d: dict, n_x: int, choice: str, keep_then: str | None = None) -> None:
    """Exactly n_x would_change items. Too many is repaired in code: surplus items are dropped from the end (new items
    are appended last), never the back-flip item (then == keep_then). Too few needs the model (feedback)."""
    wc = d["flip_conditions"]["would_change"]
    while len(wc) > n_x and keep_then is not None:
        i = next((k for k in range(len(wc) - 1, -1, -1) if wc[k]["then"] != keep_then), None)
        if i is None:
            break
        wc.pop(i)
    n = len(wc)
    if n < n_x:
        raise ValueError(f"the flip conditions must keep {n_x} would_change items; {n} remain after dropping the ones that now point at "
                         f"the verdict {choice}. Add {n_x - n} entr{'y' if n_x - n == 1 else 'ies'} to new_would_change (an independent, "
                         f"non-vacuous condition, `then` an option other than {choice}).")
    if n > n_x:
        raise ValueError(f"the flip conditions must keep exactly {n_x} would_change items; there are {n}. Send fewer new_would_change entries.")


def assert_back_flip(d: dict, x_choice: str, t_choice: str) -> str:
    """The back-flip item (then = X's choice) must exist; returns its id."""
    assert x_choice != t_choice, "flip must change the verdict"
    for w in d["flip_conditions"]["would_change"]:
        if w["then"] == x_choice:
            return w["id"]
    raise ValueError(f"no would_change item points back to the parent's choice {x_choice}")


def shuffle_and_renumber(d: dict, seed: int) -> dict[str, str]:
    """Shuffle would_change (seeded), renumber flip1..n, rewrite prose references. Returns old id -> new id."""
    wc = d["flip_conditions"]["would_change"]
    order = list(range(len(wc)))
    random.Random(seed).shuffle(order)
    new = [wc[i] for i in order]
    mp = {w["id"]: f"flip{n}" for n, w in enumerate(new, 1)}
    for w in new:
        w["id"] = mp[w["id"]]
    d["flip_conditions"]["would_change"] = new

    def fix(s):
        return PROSE_REF.sub(lambda m: "{" + mp[m.group(1)] + "}" if m.group(1) in mp else m.group(0), s) if isinstance(s, str) else s

    def walk(o):
        if isinstance(o, dict):
            return {k: walk(v) for k, v in o.items()}
        if isinstance(o, list):
            return [walk(v) for v in o]
        return fix(o)
    for key in ("situation", "lesson", "limits"):
        d[key] = fix(d[key])
    for key in ("reasoning", "considerations"):
        d[key] = walk(d[key])
    fc = d["flip_conditions"]
    for key in ("would_change", "would_not_change", "watch_for"):
        for w in fc.get(key, []):
            w["why"] = fix(w["why"])
    return mp
