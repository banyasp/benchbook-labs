"""Where 2e finds each scorer's value inside the dict `scorers.score_reply` returns.

2d's key names are not frozen in INTERFACES.md ("one entry per PDF table row"), so every lookup goes through
this one table. At integration run `python -m eval.score_names <samples.jsonl>` to list the keys actually seen,
then fix the aliases here (first alias present wins). A metric with no alias present is reported as n/a.
"""
from __future__ import annotations

import json
import sys

ALIASES: dict[str, list[str]] = {
    "choice": ["choice", "verdict_choice", "decision", "choice_correct", "decision_correct"],
    "relation": ["relation", "relation_correct", "relation_accuracy", "relation_map"],
    "via": ["via", "via_correct", "via_accuracy"],
    # options-enumeration score (found/extra form) and the gold options the agent failed to enumerate
    "options_enumeration": ["options_enumeration", "options_enum", "options", "option_enumeration"],
    "options_omitted": ["options_omitted", "gold_options_omitted", "gold_option_omissions", "options_missing"],
    "gold_option_present": ["gold_option_enumerated", "gold_option_present", "choice_option_enumerated"],
    "schema": ["schema_validator", "schema", "format"],
    # the gold id the agent's verdict choice was translated to (judge alignment), if 2d exposes it as a score
    "translated_choice": ["translated_choice", "choice_gold_id"],
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
