"""score_reply: every row of the PDF's scoring table (v0.4 pp. 23-24), each its own value. No weights, no
combination, no gate penalty -- the reward function is Peter's (TBD).

    scores = score_reply(parsed, key, served, judge)            # flat {row: float | int | None}
    full = score_reply_detailed(parsed, key, served, judge)     # .rows (same dict) + .details (alignments, paths)

`served`: a ServedCase, a list of them (REF1, REF2... in serving order), or None (no-reference arm).

Headline rows (ROWS) are the PDF's rows plus the additions DECISIONS 2026-10-25 asks for; dotted keys
(`facts_enum.found`, `facts_mapping.live_only.both`...) are the components each headline value was computed from,
exposed so the reward can weight partitions without rescoring. A row is None when its gold is absent or it comes
after the agent's not_governed; see rows.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bench.schema import AnswerKey, ParsedReply, ServedCase

from . import rows as R
from .judge import Judge

# PDF row -> headline key (in table order). `+` marks additions to the PDF table.
ROWS = [
    "schema_valid",                                   # Overall schema: SCHEMA_VALIDATOR 0/1
    "facts_enum",                                     # Facts enumeration: ENUM_GRADER
    "frame_question", "frame_decider", "frame_role",  # Frame articulation x3: Jev_Noul
    "options_enum",                                   # Options enumeration: ENUM_GRADER
    "options_omitted", "options_correct_omitted",     # + gold options never enumerated (DECISIONS)
    "frame_map_question", "frame_map_decider", "frame_map_role",   # Frame mapping x3: exact
    "options_mapping",                                # + fact_mapping.options vs key.option_map
    "facts_mapping",                                  # Facts mapping: translate -> SET_COMPARE
    "considerations_enum",                            # Considerations enumeration: ENUM_GRADER ...
    "considerations_enum.facts", "considerations_enum.favors",     # ... + per consideration SET_COMPARE
    "considerations_enum.equity", "considerations_enum.weight",
    "considerations_mapping",                         # Considerations mapping: translate -> SET_COMPARE
    "governs",                                        # Applicability: exact
    "verdict_choice",                                 # Choice: translate -> exact
    "course",                                         # Course: Jev_Noul
    "relation",                                       # Relation: exact
    "via_match", "via_consistent",                    # + via (DECISIONS): vs gold; choice vs the item's then
    "decisive",                                       # Decisive considerations: SET_COMPARE
    "now",                                            # What to do now: ENUM_GRADER
    "flip_conditions",                                # Flip conditions: ENUM_GRADER
    "flip_conditions.then",                           # + then accuracy on aligned flips
]
# Diagnostics: reported, never for reward.
DIAGNOSTICS = ["verdict_choice_ungated", "format.steps_present", "format.steps_missing", "format.steps_malformed",
               "format.steps_repaired", "format.in_order", "format.agent_not_governed"]


@dataclass
class ReplyScores:
    rows: dict[str, float | int | None]
    details: dict[str, Any] = field(default_factory=dict)


def _served_list(served) -> list[ServedCase]:
    if served is None:
        return []
    return list(served) if isinstance(served, (list, tuple)) else [served]


def _sc(name: str, d: dict | None, keys=("key_only", "both", "agent_only")) -> dict:
    """Flatten a SET_COMPARE / mapping result."""
    if d is None:
        return {name: None}
    out = {name: d["score"]}
    for k, v in d.items():
        if isinstance(v, dict) and set(keys) <= set(v):
            for kk in keys:
                out[f"{name}.{k}.{kk}"] = v[kk]
        elif k in keys:
            out[f"{name}.{k}"] = v
    return out


def score_reply_detailed(parsed: ParsedReply, key: AnswerKey, served, judge: Judge, *,
                         threshold: float | None = None, weights: dict | None = None) -> ReplyScores:
    """weights: optional per-scorer weight overrides, e.g. {"facts_enum": {"w_extra": 0.5}, "facts_mapping":
    {"w_agent_only": 1.0}} (keys: facts_enum, options_enum, considerations_enum, now, flip_conditions for ENUM;
    facts_mapping, considerations_mapping, decisive for SET_COMPARE)."""
    w = weights or {}
    ctx = R.ScoringContext(parsed, key, _served_list(served), judge,
                           **({"threshold": threshold} if threshold is not None else {}))
    rows: dict[str, Any] = {}
    fr = R.format_report(parsed)
    rows["schema_valid"] = R.schema_valid(ctx)

    fe = R.facts_enumeration(ctx, **w.get("facts_enum", {}))
    rows.update(fe.flat("facts_enum") if fe else {"facts_enum": None})
    for k in ("question", "decider", "role"):
        rows[f"frame_{k}"] = R.frame_articulation(ctx, k)
    rows.update(R.options_enumeration(ctx, **w.get("options_enum", {})).flat("options_enum"))
    rows.update(R.options_omitted(ctx))
    for k in ("question", "decider", "role"):
        rows[f"frame_map_{k}"] = R.frame_mapping(ctx, k)
    om = R.options_mapping(ctx)
    rows["options_mapping"] = om["score"] if om else None
    rows.update(_sc("facts_mapping", R.mapping_compare(ctx, "fact", **w.get("facts_mapping", {}))))

    ce = R.considerations_enumeration(ctx, **w.get("considerations_enum", {}))
    if ce is None:
        rows.update({k: None for k in ROWS if k.startswith("considerations_enum")})
    else:
        rows.update(ce["enum"].flat("considerations_enum"))
        for k in ("facts", "favors", "equity", "weight"):
            rows[f"considerations_enum.{k}"] = ce[k]
    cm = R.mapping_compare(ctx, "consideration", **w.get("considerations_mapping", {}))
    rows.update(_sc("considerations_mapping", cm))

    rows["governs"] = R.applicability_governs(ctx)
    rows["verdict_choice"] = R.verdict_choice(ctx)
    rows["verdict_choice_ungated"] = R.verdict_choice(ctx, gate=False)
    rows["course"] = R.verdict_course(ctx)
    rows["relation"] = R.verdict_relation(ctx)
    rows["via_match"] = R.via_match(ctx)
    rows["via_consistent"] = R.via_consistent(ctx)
    rows.update(_sc("decisive", R.verdict_decisive(ctx, **w.get("decisive", {}))))
    now = R.verdict_now(ctx, **w.get("now", {}))
    rows.update(now.flat("now") if now else {"now": None})
    fl = R.verdict_flip_conditions(ctx, **w.get("flip_conditions", {}))
    if fl is None:
        rows.update({"flip_conditions": None, "flip_conditions.then": None})
    else:
        rows.update(fl["enum"].flat("flip_conditions"))
        rows["flip_conditions.then"] = fl["then"]

    rows["format.steps_present"] = len(fr["present"])
    rows["format.steps_missing"] = len(fr["missing"])
    rows["format.steps_malformed"] = len(fr["malformed"])
    rows["format.steps_repaired"] = len(fr["repaired"])
    rows["format.in_order"] = int(fr["in_order"])
    rows["format.agent_not_governed"] = int(ctx.agent_not_governed)

    details = {"format_report": fr, "notes": ctx.notes, "option_alignment": ctx.option_al.to_dict(),
               "fact_alignment": ctx.fact_al.to_dict() if ctx.fact_al else None,
               "consideration_alignment": ctx.cons_al.to_dict() if ctx.cons_al else None,
               "options_mapping": om, "considerations_per": ce["per"] if ce else None,
               "facts_mapping": R.mapping_compare(ctx, "fact") if key.fact_mapping is not None else None,
               "considerations_mapping": cm}
    return ReplyScores(rows, details)


def score_reply(parsed: ParsedReply, key: AnswerKey, served, judge: Judge, **kw) -> dict[str, float | int | None]:
    return score_reply_detailed(parsed, key, served, judge, **kw).rows
