"""Where 2e finds each scorer's value inside the dict `scorers.score_reply` returns.

2d's key names are not frozen in INTERFACES.md ("one entry per PDF table row"), so every lookup goes through
this one table. At integration run `python -m eval.score_names <samples.jsonl>` to list the keys actually seen,
then fix the aliases here (first alias present wins). A metric with no alias present is reported as n/a.
"""
from __future__ import annotations

import json
import sys

ALIASES: dict[str, list[str]] = {
    # Fixed at integration (2026-10-25) to 2d's real keys (scorers/score.py). Eval reports the UNGATED choice:
    # Later aliases are generic fallbacks (test fakes). decoy-arm accuracy must count a not_governed decline's choice (never use the ungated value for reward).
    "choice": ["verdict_choice_ungated", "choice"],
    "choice_gated": ["verdict_choice"],
    "relation": ["relation"],
    "via": ["via_match", "via"],
    "via_consistent": ["via_consistent"],
    "options_enumeration": ["options_enum", "options_enumeration"],
    "options_omitted": ["options_omitted"],
    "gold_option_present": ["gold_option_present"],          # derived in eval.core.score_reply_with_details
    "schema": ["schema_valid", "schema"],
    "translated_choice": ["translated_choice"],              # derived in eval.core.score_reply_with_details
}


def get(scores: dict | None, metric: str):
    """First alias of `metric` present in `scores` (value may be None = not scored), else None."""
    for k in ALIASES.get(metric, [metric]):
        if scores and k in scores:
            return scores[k]
    return None


def has(scores: dict | None, metric: str) -> bool:
    return any(scores and k in scores for k in ALIASES.get(metric, [metric]))


def main(path: str):
    keys: dict[str, int] = {}
    for line in open(path):
        for k in (json.loads(line).get("scores") or {}):
            keys[k] = keys.get(k, 0) + 1
    for k, n in sorted(keys.items()):
        used = [m for m, al in ALIASES.items() if k in al]
        print(f"{k:40s} n={n:6d}  used_as={used or '-'}")
    for m, al in ALIASES.items():
        if not any(k in keys for k in al):
            print(f"NO SCORE FOR METRIC `{m}` (aliases {al})")


if __name__ == "__main__":
    main(sys.argv[1])
