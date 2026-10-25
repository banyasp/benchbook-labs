"""Statistics over samples.jsonl: bootstrap CIs resampling whole case FAMILIES, paired differences, the
"copy the case's verdict" baseline (PDF falsification test 4) and shortcut-cue checks over the gold.

Why families: variants of one family (restyle, trap, flips of INT-301...) share a source case and are not
independent; resampling samples or scenarios would give CIs that are far too narrow.

    PYTHONPATH=code .venv/bin/python -m eval.stats results/checkpoint2/<run>/samples.jsonl [--out stats.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from . import score_names
from .core import MODES, read_samples

N_BOOT = 2000


# ------------------------------------------------------------------ bootstrap
def _per_family(rows: Iterable[dict], value: Callable[[dict], float | None]):
    s, c = defaultdict(float), defaultdict(int)
    for r in rows:
        v = value(r)
        if v is None:
            continue
        s[r["family"]] += float(v)
        c[r["family"]] += 1
    return s, c


def family_bootstrap(rows, value, n_boot: int = N_BOOT, seed: int = 0, alpha: float = 0.05) -> dict:
    """Mean of `value` over all rows, 95% percentile CI by resampling families with replacement (ratio estimator:
    families with more samples weigh more, as in the pooled mean)."""
    s, c = _per_family(rows, value)
    fams = sorted(c)
    n = sum(c.values())
    if n == 0:
        return {"mean": None, "lo": None, "hi": None, "n": 0, "n_families": 0}
    S = np.array([s[f] for f in fams])
    C = np.array([c[f] for f in fams], dtype=float)
    mean = float(S.sum() / C.sum())
    if len(fams) < 2:
        return {"mean": mean, "lo": mean, "hi": mean, "n": n, "n_families": len(fams), "few_families": True}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(fams), size=(n_boot, len(fams)))
    num, den = S[idx].sum(1), C[idx].sum(1)
    ok = den > 0
    est = num[ok] / den[ok]
    lo, hi = np.quantile(est, [alpha / 2, 1 - alpha / 2])
    return {"mean": mean, "lo": float(lo), "hi": float(hi), "n": n, "n_families": len(fams),
            "few_families": len(fams) < 5}


def family_bootstrap_diff(rows_a, rows_b, value, n_boot: int = N_BOOT, seed: int = 0, alpha: float = 0.05) -> dict:
    """mean(a) - mean(b), families resampled jointly (a family absent from one side contributes nothing there)."""
    sa, ca = _per_family(rows_a, value)
    sb, cb = _per_family(rows_b, value)
    fams = sorted(set(ca) | set(cb))
    if not ca or not cb:
        return {"diff": None, "lo": None, "hi": None, "n_families": len(fams)}
    A = np.array([[sa.get(f, 0.0), ca.get(f, 0)] for f in fams], dtype=float)
    B = np.array([[sb.get(f, 0.0), cb.get(f, 0)] for f in fams], dtype=float)
    diff = float(A[:, 0].sum() / A[:, 1].sum() - B[:, 0].sum() / B[:, 1].sum())
    if len(fams) < 2:
        return {"diff": diff, "lo": diff, "hi": diff, "n_families": len(fams), "few_families": True}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(fams), size=(n_boot, len(fams)))
    a, b = A[idx].sum(1), B[idx].sum(1)
    ok = (a[:, 1] > 0) & (b[:, 1] > 0)
    est = a[ok, 0] / a[ok, 1] - b[ok, 0] / b[ok, 1]
    lo, hi = np.quantile(est, [alpha / 2, 1 - alpha / 2])
    return {"diff": diff, "lo": float(lo), "hi": float(hi), "n_families": len(fams), "few_families": len(fams) < 5}


# ------------------------------------------------------------------ per-record metrics
def choice_correct(r) -> float | None:
    """1/0 by the scorer's choice score. A reply with no parsed verdict choice counts as wrong (0), because the
    scorer's None means "not scored" and a missing verdict is a failure, not an absence of gold."""
    if r.get("parsed_choice") is None:
        return 0.0
    v = r.get("choice_score")
    return None if v is None else float(v)


def _score(metric):
    def f(r):
        v = score_names.get(r.get("scores"), metric)
        return None if v is None else float(v)
    return f


METRICS: dict[str, Callable[[dict], float | None]] = {
    "choice_acc": choice_correct,
    "strict_ok": lambda r: float(r["format"]["strict_ok"]),
    "steps_present": lambda r: float(not r["format"]["missing"]),
    "has_verdict": lambda r: float(r.get("parsed_choice") is not None),
    "options_enumerated": lambda r: float(r["n_model_options"]),
    "options_score": _score("options_enumeration"),
    "gold_option_omitted": lambda r: (None if score_names.get(r.get("scores"), "gold_option_present") is None
                                      else 1.0 - float(score_names.get(r["scores"], "gold_option_present"))),
    "options_omitted": _score("options_omitted"),
    "relation_acc": _score("relation"),
    "via_acc": _score("via"),
    "tokens_completion": lambda r: r["tokens"].get("completion"),
    "tokens_prompt": lambda r: r["tokens"].get("prompt"),
    "tokens_thinking": lambda r: r["tokens"].get("thinking"),
    "seconds": lambda r: r.get("seconds"),
    "hit_length_cap": lambda r: float(r.get("finish_reason") == "length"),
}


def cell_key(r) -> tuple:
    return (r["mode"], r["arm"], bool(r["analogical_prompt"]))


def group_cells(rows) -> dict[tuple, list[dict]]:
    g = defaultdict(list)
    for r in rows:
        g[cell_key(r)].append(r)
    return dict(g)


def cell_summary(rows, n_boot: int = N_BOOT) -> dict:
    return {m: family_bootstrap(rows, f, n_boot) for m, f in METRICS.items()}


# ------------------------------------------------------------------ copy baseline and cues
def unique_scenario_arm(rows) -> list[dict]:
    seen, out = set(), []
    for r in rows:
        k = (r["scenario"], r["arm"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def copy_baseline(rows, n_boot: int = N_BOOT) -> dict:
    """Accuracy of 'copy the served case's verdict' per arm, over unique (scenario, arm), with coverage: how many
    had a translatable verdict. Untranslatable (option_map missing or no mapped option) counts as wrong in
    `acc_all`; `acc_translatable` drops them. Decoys normally have no option_map, so read their numbers as 0-cover."""
    out = {}
    for arm in sorted({r["arm"] for r in rows}):
        u = [r for r in unique_scenario_arm(rows) if r["arm"] == arm]
        avail = [r for r in u if r["copy_baseline"]["available"]]
        out[arm] = {
            "n_scenarios": len(u), "n_available": len(avail),
            "acc_all": family_bootstrap([r for r in u], lambda r: float(bool(r["copy_baseline"]["correct"])), n_boot)
            if arm != "none" else None,
            "acc_translatable": family_bootstrap(avail, lambda r: float(r["copy_baseline"]["correct"]), n_boot),
        }
    return out


def shortcut_cues(rows) -> dict:
    """Cues in the GOLD (per unique scenario x arm) and in the model's behaviour. Flags are heuristics: look at the
    numbers, not only the flags."""
    u = unique_scenario_arm(rows)
    n = len(u)
    if not n:
        return {}
    pos = Counter(r["cues"]["gold_position"] for r in u)
    nopt = Counter(r["cues"]["n_gold_options"] for r in u)
    moves = Counter(r["cues"]["gold_move"] for r in u)
    hand_up = sum(bool(r["cues"]["gold_is_hand_up"]) for r in u) / n
    longest = sum(bool(r["cues"]["gold_is_longest"]) for r in u) / n
    shortest = sum(bool(r["cues"]["gold_is_shortest"]) for r in u) / n
    chance_longest = float(np.mean([1.0 / r["cues"]["n_gold_options"] for r in u]))
    ratio = [r["cues"]["gold_len_chars"] / r["cues"]["mean_other_len"] for r in u if r["cues"].get("mean_other_len")]
    top_pos, top_n = pos.most_common(1)[0]
    chance_pos = float(np.mean([1.0 / r["cues"]["n_gold_options"] for r in u]))
    model_first = [r for r in rows if r.get("model_choice_position") is not None]
    acc_by_pos = {}
    for p in sorted(pos):
        sub = [r for r in rows if r["cues"]["gold_position"] == p]
        acc_by_pos[p] = family_bootstrap(sub, choice_correct, 300)
    flags = []
    if top_n / n > chance_pos + 0.2:
        flags.append(f"gold is option #{top_pos + 1} in {top_n / n:.0%} of scenario-arms (chance ~{chance_pos:.0%})")
    if hand_up > 0.5:
        flags.append(f"gold is a hand-up move (ask/refuse) in {hand_up:.0%}")
    if longest > chance_longest + 0.2:
        flags.append(f"gold is the longest option in {longest:.0%} (chance ~{chance_longest:.0%})")
    if shortest > chance_longest + 0.2:
        flags.append(f"gold is the shortest option in {shortest:.0%} (chance ~{chance_longest:.0%})")
    mf = (sum(r["model_choice_position"] == 0 for r in model_first) / len(model_first)) if model_first else None
    if mf is not None and mf > 0.6:
        flags.append(f"the model picks its first-listed option in {mf:.0%} of replies")
    return {"n_scenario_arms": n, "gold_position_counts": dict(sorted(pos.items())), "n_options_counts": dict(nopt),
            "gold_move_counts": dict(moves), "gold_hand_up_rate": hand_up, "gold_longest_rate": longest,
            "gold_shortest_rate": shortest, "chance_longest": chance_longest,
            "gold_len_over_mean_other": float(np.mean(ratio)) if ratio else None,
            "model_first_option_rate": mf, "acc_by_gold_position": acc_by_pos, "flags": flags}


# ------------------------------------------------------------------ headline contrasts
def contrasts(rows, n_boot: int = N_BOOT) -> list[dict]:
    """The PDF's falsification comparisons that exist at Checkpoint 2 (base model only), per mode and prompt flag:
    relevant - none, augmented - none, decoy - none (test 3: negative = decoys mislead), relevant - decoy, and
    relevant - copy baseline (test 4, as a paired difference on the same scenarios, prompt/mode-matched)."""
    out = []
    cells = group_cells(rows)
    for mode in MODES:
        for p in (True, False):
            def get(arm):
                return cells.get((mode, arm, p), [])
            for a, b in (("relevant", "none"), ("augmented", "none"), ("decoy", "none"), ("relevant", "decoy"),
                         ("relevant", "augmented")):
                ra, rb = get(a), get(b)
                if ra and rb:
                    d = family_bootstrap_diff(ra, rb, choice_correct, n_boot)
                    out.append({"mode": mode, "prompt": p, "a": a, "b": b, **d})
            rel = get("relevant")
            av = [r for r in rel if r["copy_baseline"]["available"]]
            if av:
                v_model = family_bootstrap(av, choice_correct, n_boot)
                v_copy = family_bootstrap(av, lambda r: float(r["copy_baseline"]["correct"]), n_boot)
                out.append({"mode": mode, "prompt": p, "a": "relevant", "b": "copy_case_verdict",
                            "diff": v_model["mean"] - v_copy["mean"], "model": v_model, "copy": v_copy,
                            **_paired_vs_copy(av, n_boot)})
    return out


def _paired_vs_copy(rows, n_boot):
    """Per-family paired diff of model accuracy minus copy-baseline accuracy over the same rows."""
    f = lambda r: choice_correct(r) - float(r["copy_baseline"]["correct"]) if choice_correct(r) is not None else None  # noqa: E731
    b = family_bootstrap(rows, f, n_boot)
    return {"lo": b["lo"], "hi": b["hi"], "n_families": b["n_families"]}


def summarize(rows, n_boot: int = N_BOOT) -> dict:
    cells = group_cells(rows)
    return {"n_samples": len(rows), "n_families": len({r["family"] for r in rows}),
            "cells": {"|".join(map(str, k)): cell_summary(v, n_boot) for k, v in sorted(cells.items())},
            "copy_baseline": copy_baseline(rows, n_boot), "cues": shortcut_cues(rows),
            "contrasts": contrasts(rows, n_boot)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("samples")
    ap.add_argument("--out", default=None, help="default: stats.json next to samples.jsonl")
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    a = ap.parse_args(argv)
    rows = read_samples(a.samples)
    s = summarize(rows, a.n_boot)
    out = Path(a.out) if a.out else Path(a.samples).with_name("stats.json")
    out.write_text(json.dumps(s, indent=2, default=str))
    print(f"wrote {out}: {s['n_samples']} samples, {s['n_families']} families", file=sys.stderr)
    for f in s["cues"].get("flags", []):
        print("SHORTCUT CUE:", f, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
