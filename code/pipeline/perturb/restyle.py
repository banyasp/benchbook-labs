"""restyle: rewrite the surface of F and Q (and the prose of A); everything structural is unchanged.

Gold: every fact matched, options 1:1 (same ids), every consideration matched; relation follows, by-construction.
"""
from __future__ import annotations

import copy
import json
import re

from bench.schema import Case
from bench.schema.common import PROSE_REF

from .common import (Ctx, apply_text, assemble, build_skeleton, mean_surface_distance, next_id, option_spread, prose_fields,
                     seed_rng)
from .numnorm import drift
from .overlap import jaccard

MIN_SURFACE = 0.3        # mean (1 - word Jaccard) over facts must reach this, else the rewrite is too timid

TASK = """TASK (restyle): produce a new surface for this whole scenario and its answer. Keep every id, every structural field
(fact kinds/statuses, option moves, considerations' facts/equity/favors/weight, verdict, which items cite which) exactly as
they are: only the wording changes. Rewrite: setting, decider, agent, situation, question, every option, every fact,
every consideration's why, every reasoning field (read, weighing, tradecraft, uncertainty, handoff, tempting_wrong.pull and
.why_wrong, rejected), every flip item (flip/noflip: if and why; watch: what and why), lesson and limits. In the reply give
considerations as {"C1": {"why": "..."}}, flip as {"flip1": {"if": "...", "why": "..."}, "watch1": {"what": "...", "why": "..."}},
facts as {"F1": "..."}, options as {"O1": "..."}, and reasoning as in the bundle (tempting_wrong without its option).
The situation must stay consistent with the facts. Every number, date, time and amount in a fact must be kept with the same value
(you may change formatting, e.g. "$1,200" as "1200 dollars", but not the value). Choose one new register for the whole scenario."""


def decisive_facts(case) -> list[str]:
    """Fact ids cited by the decisive considerations (R43)."""
    dec = set(case.verdict.decisive)
    return sorted({f for c in case.considerations if c.id in dec for f in c.facts}, key=lambda i: int(i[1:]))


def restyle(X, store, rng):
    ctx = Ctx("restyle", X, store, rng)
    dec_facts = decisive_facts(X.case)
    orig_text = {f.id: f.fact for f in X.case.facts}
    sk = build_skeleton(X, [], rng, remap_prose=False)
    sections = {"fq", "a"}
    from .common import bundle
    user = TASK + "\n\nBUNDLE:\n" + json.dumps(bundle(sk.d, sections), indent=1, ensure_ascii=False)
    orig_refs = {k: set(PROSE_REF.findall(v)) for k, v in prose_fields(sk.d).items()}

    def validate(out):
        d = copy.deepcopy(sk.d)
        apply_text(d, out, sections)
        for k, v in prose_fields(d).items():
            if set(PROSE_REF.findall(v)) != orig_refs[k]:
                raise ValueError(f"{k}: keep exactly the original references {sorted(orig_refs[k])}")
        Case.model_validate({**d, "id": X.id})
        bad = []
        for f in d["facts"]:
            if f["id"] in dec_facts:
                dr = drift(orig_text[f["id"]], f["fact"])
                if not dr["ok"]:
                    bad.append(f"{f['id']}: numbers/dates/amounts changed (missing {dr['missing']}, new {dr['added']}); original: "
                               f"\"{orig_text[f['id']]}\"")
        if bad:
            raise ValueError("numeric drift in decisive facts (every number, date and amount in a fact that a decisive "
                             "consideration cites must survive unchanged; only the formatting may change): " + "; ".join(bad))
        dist = sum(1 - jaccard(a["fact"], b["fact"]) for a, b in zip(sk.d["facts"], d["facts"])) / len(d["facts"])
        if dist < MIN_SURFACE:
            raise ValueError(f"facts are too close to the original (surface distance {dist:.2f} < {MIN_SURFACE}); rewrite more")
        sp, sp0 = option_spread(d), option_spread(sk.d)
        if sp > max(1.3, sp0 * 1.15):
            raise ValueError(f"options must stay a matched set: longest/shortest word-count ratio is {sp} (original {sp0}); equalize their length")
        return d

    d, _ = ctx.ask("perturber", "rewrite", "rewrite", user, validate, step_id="restyle.rewrite")
    ctx.prov.fields.update({"case.situation": "restyle.rewrite", "case.reasoning": "restyle.rewrite", "case.considerations": "restyle.rewrite"})
    tid = next_id(store, X.family, "restyle")
    detail = {"surface_distance": None, "option_len_spread": {"parent": option_spread(sk.d), "child": option_spread(d)},
              "numeric_drift_in_decisive_facts": [],
              "decisive_facts_checked": dec_facts}
    T, partial = assemble(ctx, X, "restyle", tid, d, sk, "by-construction", detail, [], set(), "follows", None,
                          X.case.verdict.choice, None, {}, "restyle")
    dist = mean_surface_distance(X, T)
    T.lineage.detail["surface_distance"] = dist
    partial["distance_features"] = {"operator": "restyle", "facts_touched_by_kind": {}, "facts_rewritten": len(T.case.facts),
                                    "magnitude": dist}
    return T, partial
