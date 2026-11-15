"""Alignment and the two generic graders of the PDF (v0.4 pp. 21-23): ENUM_GRADER and SET_COMPARE.

align(generated, gold, judge) -- PDF p. 21, Fig. 6:
  1. Two Jev Choice passes. Row pass: for each gold item, P(which generated item | gold) over generated + "none".
     Column pass: for each generated item, P(which gold item | generated) over gold + "none".
  2. The two passes are overlaid as two confusion matrices (gold x generated) and combined cell by cell with the
     geometric mean S = sqrt(R * C): high only when both directions agree.
  3. Threshold: gold i is *present* iff some S[i, j] > threshold, else *absent*; generated j *covers* gold i iff
     S[i, j] > threshold.
  4. Greedy assignment (not Hungarian, PDF p. 21): visit the cells in descending order of S; record (gold, gen) unless
     either is already claimed, or S <= threshold. The recorded pairs are the translation {generated id: gold id}.
     Conflated and duplicated items therefore never score twice downstream.
  5. Partitions:
       gold  found       paired, and its partner stands for no other present-but-unpaired gold item
             conflated   present, but stated only inside a generated item that also states another gold item:
                         unpaired-but-present gold items, plus the paired gold item sharing that generated item
             absent      no generated item covers it
       gen   matched     paired with a gold item it alone stands for
             conflating  paired, and also covers a present-but-unpaired gold item (a merge)
             duplicate   unpaired, but covers some (already claimed) gold item: a restatement
             extraneous  covers no gold item

ENUM_GRADER (Fig. 6 footnote; reconciliation C2):
    score = (sum_found w_g * w_found + sum_conflated w_g * w_conflated
             - n_extraneous * w_extra - n_duplicate * w_duplicate) / sum_gold w_g
  Max 1.0 (every gold item found, nothing extra); can go negative. Hard credit (threshold), per the PDF's
  "if VAL > threshold" -- `soft=True` uses the paired S value instead of 1 for found/conflated gold.

SET_COMPARE (Fig. 8): partition counts (key_only, both, agent_only) of two sets; set_score() is an optional
  weighted sum of those counts normalized by |key| with exposed default weights.

Every default below is a placeholder for Peter: THRESHOLD, W_FOUND, W_CONFLATED, W_EXTRA, W_DUPLICATE, and the
SET_COMPARE weights.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np

from .judge import Judge

THRESHOLD = 0.5      # S above this = "present" / "covers"            (Peter: set)
W_FOUND = 1.0        # credit per found gold item (times its weight)  (Peter: set)
W_CONFLATED = 0.5    # credit per conflated-but-present gold item     (Peter: set; PDF: "its own lower reward")
W_EXTRA = 0.25       # penalty per extraneous generated item          (Peter: set)
W_DUPLICATE = 0.25   # penalty per duplicate generated item           (Peter: set; PDF silent)
SC_BOTH, SC_KEY_ONLY, SC_AGENT_ONLY = 1.0, 0.0, 0.5   # SET_COMPARE weights (Peter: set; PDF: "weights TBD")


@dataclass
class Alignment:
    gold_ids: list[str]
    gen_ids: list[str]
    R: list[list[float]]           # gold x (gen + none): row pass
    C: list[list[float]]           # (gold + none) x gen: column pass
    S: list[list[float]]           # gold x gen: geometric mean
    threshold: float
    pairs: list[tuple[str, str, float]] = field(default_factory=list)      # (gold, gen, S) in greedy order
    translation: dict[str, str] = field(default_factory=dict)             # gen id -> gold id
    covers: dict[str, list[str]] = field(default_factory=dict)            # gen id -> gold ids with S > threshold
    found: list[str] = field(default_factory=list)
    conflated: list[str] = field(default_factory=list)
    absent: list[str] = field(default_factory=list)
    matched_gen: list[str] = field(default_factory=list)
    conflating: list[str] = field(default_factory=list)
    duplicate: list[str] = field(default_factory=list)
    extraneous: list[str] = field(default_factory=list)

    @property
    def present(self) -> list[str]:
        return self.found + self.conflated

    def gold_for(self, gen_id: str) -> str | None:
        return self.translation.get(gen_id)

    def to_dict(self) -> dict:
        return asdict(self)


def greedy_pairs(S: np.ndarray, threshold: float) -> list[tuple[int, int, float]]:
    """PDF p. 21: descending order of S; record a pair unless either side is already covered. Ties break by
    (gold index, gen index) so the result is deterministic."""
    cells = sorted(((float(S[i, j]), i, j) for i in range(S.shape[0]) for j in range(S.shape[1])),
                   key=lambda x: (-x[0], x[1], x[2]))
    used_g, used_l, out = set(), set(), []
    for s, i, j in cells:
        if s <= threshold:
            break
        if i in used_g or j in used_l:
            continue
        used_g.add(i), used_l.add(j)
        out.append((i, j, s))
    return out


def align_from_passes(R, C, gold_ids: list[str], gen_ids: list[str], threshold: float = THRESHOLD) -> Alignment:
    """The deterministic half of align(): R gold x (gen+1), C (gold+1) x gen, both as the judge returned them."""
    ng, nl = len(gold_ids), len(gen_ids)
    R = np.asarray(R, float).reshape(ng, nl + 1) if ng else np.zeros((0, nl + 1))
    C = np.asarray(C, float).reshape(ng + 1, nl) if nl else np.zeros((ng + 1, 0))
    S = np.sqrt(np.clip(R[:, :nl], 0, None) * np.clip(C[:ng, :], 0, None)) if ng and nl else np.zeros((ng, nl))
    pairs = greedy_pairs(S, threshold)
    paired_g = {i: j for i, j, _ in pairs}
    paired_l = {j: i for i, j, _ in pairs}
    cover = {j: [i for i in range(ng) if S[i, j] > threshold] for j in range(nl)}
    present = {i for i in range(ng) if nl and S[i].max() > threshold}
    unpaired_present = present - set(paired_g)
    conflating = {j for j in paired_l if any(i in unpaired_present for i in cover[j])}
    conflated = unpaired_present | {paired_l[j] for j in conflating}
    found = [i for i in range(ng) if i in paired_g and i not in conflated]
    al = Alignment(
        gold_ids=list(gold_ids), gen_ids=list(gen_ids), R=R.round(6).tolist(), C=C.round(6).tolist(),
        S=S.round(6).tolist(), threshold=threshold,
        pairs=[(gold_ids[i], gen_ids[j], round(s, 6)) for i, j, s in pairs],
        translation={gen_ids[j]: gold_ids[i] for i, j, _ in pairs},
        covers={gen_ids[j]: [gold_ids[i] for i in cover[j]] for j in range(nl)},
        found=[gold_ids[i] for i in found],
        conflated=[gold_ids[i] for i in sorted(conflated)],
        absent=[gold_ids[i] for i in range(ng) if i not in present],
        matched_gen=[gen_ids[j] for j in sorted(paired_l) if j not in conflating],
        conflating=[gen_ids[j] for j in sorted(conflating)],
        duplicate=[gen_ids[j] for j in range(nl) if j not in paired_l and cover[j]],
        extraneous=[gen_ids[j] for j in range(nl) if not cover[j]],
    )
    return al


def align(generated: dict[str, str], gold: dict[str, str], judge: Judge, threshold: float = THRESHOLD,
          instruction: str | None = None, context: str | None = None) -> Alignment:
    """Two Choice passes + geometric mean + greedy assignment. `generated`, `gold`: {id: text}."""
    gen_ids, gen_txt = list(generated), [str(v) for v in generated.values()]
    gold_ids, gold_txt = list(gold), [str(v) for v in gold.values()]
    if not gen_ids or not gold_ids:
        return align_from_passes(np.zeros((len(gold_ids), len(gen_ids) + 1)),
                                 np.zeros((len(gold_ids) + 1, len(gen_ids))), gold_ids, gen_ids, threshold)
    reqs = ([{"item": g, "candidates": gen_txt, "context": context, "instruction": instruction} for g in gold_txt]
            + [{"item": l, "candidates": gold_txt, "context": context, "instruction": instruction} for l in gen_txt])
    res = judge.choice_many(reqs)
    R = np.array(res[:len(gold_ids)], float)                  # gold x (gen + none)
    C = np.array(res[len(gold_ids):], float).T                # (gold + none) x gen
    return align_from_passes(R, C, gold_ids, gen_ids, threshold)


# ---------------------------------------------------------------- ENUM_GRADER
@dataclass
class EnumScore:
    score: float | None
    n_gold: int
    n_generated: int
    found: int
    conflated: int
    absent: int
    extraneous: int
    duplicate: int

    def flat(self, name: str) -> dict:
        d = {name: self.score}
        for k in ("n_gold", "n_generated", "found", "conflated", "absent", "extraneous", "duplicate"):
            d[f"{name}.{k}"] = getattr(self, k)
        return d


def enum_grade(al: Alignment, gold_weights: dict[str, float] | None = None, w_found: float = W_FOUND,
               w_conflated: float = W_CONFLATED, w_extra: float = W_EXTRA, w_duplicate: float = W_DUPLICATE,
               soft: bool = False) -> EnumScore:
    """PDF ENUM_GRADER: sum found*w_found + conflated*w_conflated - extra*w_extra, normalized by |gold| (weighted).
    None when there is no gold."""
    gw = {g: (gold_weights or {}).get(g, 1.0) for g in al.gold_ids}
    s_of = {g: s for g, _, s in al.pairs}
    credit = (lambda g: s_of.get(g, 1.0)) if soft else (lambda g: 1.0)
    total = sum(gw.values())
    if not al.gold_ids or total <= 0:
        score = None
    else:
        score = (sum(gw[g] * w_found * credit(g) for g in al.found)
                 + sum(gw[g] * w_conflated * credit(g) for g in al.conflated)
                 - w_extra * len(al.extraneous) - w_duplicate * len(al.duplicate)) / total
    return EnumScore(score, len(al.gold_ids), len(al.gen_ids), len(al.found), len(al.conflated), len(al.absent),
                     len(al.extraneous), len(al.duplicate))


# ---------------------------------------------------------------- SET_COMPARE
def set_compare(key, agent) -> dict[str, int]:
    k, a = set(key or ()), set(agent or ())
    return {"key_only": len(k - a), "both": len(k & a), "agent_only": len(a - k)}


def set_score(counts: dict[str, int] | list[dict[str, int]], w_both: float = SC_BOTH,
              w_key_only: float = SC_KEY_ONLY, w_agent_only: float = SC_AGENT_ONLY) -> float:
    """Weighted sum of SET_COMPARE partitions normalized by |key| (summed over several partitions if a list).
    Two empty sets score 1.0 (nothing to find, nothing invented); max 1.0."""
    cs = counts if isinstance(counts, list) else [counts]
    both = sum(c["both"] for c in cs)
    ko = sum(c["key_only"] for c in cs)
    ao = sum(c["agent_only"] for c in cs)
    n_key = both + ko
    if n_key == 0:
        return 1.0 if ao == 0 else -w_agent_only * ao
    return (w_both * both - w_key_only * ko - w_agent_only * ao) / n_key
