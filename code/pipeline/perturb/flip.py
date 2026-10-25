"""flip: realize ONE would_change item indirectly (design 4a), update A to the item's `then`, restyle the rest lightly.

Gold (by-construction): relation flips, via = the C would_change item, choice = T's counterpart of its `then`
(options are 1:1 and keep their ids). Facts the realization replaced are `corresponding`, added ones `live_only`,
removed ones `case_only`, the rest `matched`; the touched consideration is `corresponding` (or `case_only` if dropped).
Indirectness: overlap(new fact text, `if` text) must pass (overlap.py) and an LLM check must confirm the condition holds.
"""
from __future__ import annotations

import copy
import json
import random

from bench.schema import Case
from bench.schema.pipeline import Touched

from .common import (Ctx, Edit, KINDS, OperatorError, STATUSES, apply_structure, apply_text, assemble, build_skeleton, bundle,
                     finish_flip_conditions, kind_counts, mean_surface_distance, next_id, option_spread)
from .overlap import MAX_RECALL, MAX_RUN, overlap

MIN_SURFACE = 0.25

TASK = """TASK (flip): the scenario's facts were changed (fixed items below are the changed or added facts; they are given as
{"text": ..., "fixed": true}). Because of that change the best decision is now {then} ("{then_do}"), not {c_choice}.
Rewrite the whole bundle as a coherent, complete scenario and answer for these facts:
- Lightly restyle (new wording, same content) the setting, decider, agent, situation, question, options and the unfixed facts,
  so the result is not the original plus one changed sentence. Keep every id. The situation must be consistent with the
  fixed facts. Reply facts as {"F1": "..."} (copy fixed ones verbatim) and options as {"O1": "..."}.
- Considerations: for each give its new "why" as {"C1": {"why": "..."}}. For {touched} (whose basis the change affects),
  and any other that is affected, also give the updated "facts" (use the T fact ids in the bundle), "favors", "weight" and,
  for a bar, "rules_out". A consideration that no longer applies at all may be {"drop": true}. You may add
  "new_considerations" (facts, equity, favors, weight, why). "decisive": the ids that decide for {then}.
- Reasoning: rewrite every field so it reaches {then}. "tempting_wrong": {"option": <an option id other than {then}>, "pull",
  "why_wrong"}; "rejected": {<option id other than {then}>: why rejected}.
- Flip items: restyle each. Item {fired} must now read as the REVERSAL: its "if" states, in new words, the condition under
  which {c_choice} would be right again (the opposite of the change that was made). Their "then" values are handled by the
  system; do not give them. Other items keep their meaning; if one is now meaningless give it a neutral rewrite anyway.
  You may add "new_would_change": [{"if", "then", "why"}].
- lesson and limits: rewrite so they fit the new outcome. Prose references use the T ids in the bundle ({F3}, {C2}, {O1})."""


def _fact_lines(d_facts) -> str:
    return "\n".join(f"{f['id']} [{f['kind']}, {f['status']}]: {f['fact']}" for f in d_facts)


def flip(X, store, rng, *, item: str | None = None):
    C = X.case
    cands = [w for w in C.flip_conditions.would_change if w.then != C.verdict.choice]
    if item:
        cands = [w for w in cands if w.id == item]
    if not cands:
        raise OperatorError(f"{X.id}: no usable would_change item" + (f" `{item}`" if item else ""))
    w = rng.choice(cands)
    ctx = Ctx("flip", X, store, rng)
    scores = {}

    # ---- stage A: realize the condition indirectly
    user = (f"CONDITION TO REALIZE: {w.if_}\n(it flips the decision to {w.then}; reason: {w.why})\n\n"
            f"QUESTION: {C.question}\nOPTIONS: " + "; ".join(f"{k}: {o.do}" for k, o in C.options.items()) + "\n\nFACTS:\n"
            + "\n".join(f"{f.id} [{f.kind}, {f.status}]: {f.fact}" for f in C.facts) + "\n\nCONSIDERATIONS:\n"
            + "\n".join(f"{c.id} ({c.equity}, favors {','.join(c.favors)}, {c.weight}; facts {','.join(c.facts)}): {c.why}" for c in C.considerations))
    fact_ids = {f.id for f in C.facts}

    def validate_a(out):
        edits = []
        for e in out.get("edits") or []:
            act = e.get("action")
            if act not in ("replace", "add", "remove"):
                raise ValueError("edit action must be replace, add or remove")
            if act in ("replace", "remove") and e.get("fact") not in fact_ids:
                raise ValueError(f"edit fact `{e.get('fact')}` is not a fact id")
            if act in ("replace", "add"):
                if not isinstance(e.get("text"), str) or not e["text"].strip():
                    raise ValueError("replace/add edits need text")
                if e.get("kind", "situation") not in KINDS or e.get("status", "confirmed") not in STATUSES:
                    raise ValueError(f"kind must be one of {KINDS} and status one of {STATUSES}")
            edits.append(Edit(act, e.get("fact"), (e.get("text") or "").strip() or None, e.get("kind"), e.get("status")))
        if not any(e.action in ("replace", "add") for e in edits):
            raise ValueError("at least one replace or add edit is needed")
        if len({e.fact for e in edits if e.fact}) != len([e for e in edits if e.fact]):
            raise ValueError("one edit per fact")
        tc = out.get("touched_consideration")
        if tc not in {c.id for c in C.considerations}:
            raise ValueError("touched_consideration must be a consideration id")
        new_text = " . ".join(e.text for e in edits if e.text)
        sc = overlap(new_text, w.if_)
        scores.clear()
        scores.update(sc)
        if not sc["pass"]:
            raise ValueError(f"the new fact text overlaps the condition's wording too much (content-word recall {sc['recall']} > "
                             f"{MAX_RECALL} or run {sc['run']} > {MAX_RUN}): it reads as a paraphrase. State it in different "
                             "terms, as a magnitude, or split over facts, without the condition's words.")
        tmp = build_skeleton(X, edits, random.Random(0), remap_prose=False)
        vuser = "FACTS:\n" + _fact_lines(tmp.d["facts"]) + f"\n\nCONDITION: {w.if_}"
        try:
            v, _ = ctx.ask("perturber", "verify", "verify_condition", vuser, lambda o: o, tries=2, step_id="flip.verify")
        except OperatorError as e:
            raise ValueError(f"verification failed to run: {e}")
        if v.get("holds") is not True:
            raise ValueError(f"a strict reader could not conclude the condition from these facts ({v.get('why')}); make the change clearer")
        return edits, tc, out.get("technique"), out.get("how", ""), v

    (edits, tc, technique, how, verdict_chk), _ = ctx.ask("perturber", "realize", "realize_flip", user, validate_a, step_id="flip.realize")
    sk = build_skeleton(X, edits, rng)

    # ---- stage B: compose T's whole text and answer
    then = w.then
    fmt = dict(then=then, then_do=C.options[then].do, c_choice=C.verdict.choice, touched=tc, fired=w.id)
    user = (TASK.replace("{then}", then).replace("{then_do}", fmt["then_do"]).replace("{c_choice}", fmt["c_choice"])
            .replace("{touched}", tc).replace("{fired}", w.id)
            + "\n\nBUNDLE:\n" + json.dumps(bundle(sk.d, {"fq", "a"}, sk.fixed), indent=1, ensure_ascii=False))
    orig_con = [c.id for c in C.considerations]

    def validate_b(out):
        d = copy.deepcopy(sk.d)
        apply_text(d, out, {"fq", "a"}, sk.fixed, free_reasoning=True)
        d["verdict"]["choice"] = then
        new_con = apply_structure(d, out, then, orig_con)
        if d["reasoning"]["tempting_wrong"]["option"] == then:
            raise ValueError("tempting_wrong.option must differ from the verdict option")
        d["reasoning"]["rejected"].pop(then, None)
        fo = out.get("flip") or {}
        finish_flip_conditions(d, out, then, C.verdict.choice, fired=w.id)
        Case.model_validate({**d, "id": X.id})
        dist = mean_surface_distance_d(sk, d)
        if dist < MIN_SURFACE:
            raise ValueError(f"the unfixed facts are too close to the original (surface distance {dist:.2f}); restyle them more")
        sp, sp0 = option_spread(d), option_spread(sk.d)
        if sp > max(1.3, sp0 * 1.15):
            raise ValueError(f"options must stay a matched set: longest/shortest word-count ratio is {sp} (original {sp0}); equalize their length")
        return d, new_con

    (d, new_con), _ = ctx.ask("perturber", "compose", "rewrite", user, validate_b, step_id="flip.compose")
    ctx.prov.fields.update({"case.considerations": "flip.compose", "case.reasoning": "flip.compose", "case.flip_conditions": "flip.compose"})
    tid = next_id(store, X.family, "flip")
    detail = {"via": C.global_id(w.id), "technique": technique, "how": how,
              "indirectness": {**scores, "max_recall": MAX_RECALL, "max_run": MAX_RUN, "if_text": w.if_},
              "verified_by_model": verdict_chk, "touched_consideration": C.global_id(tc),
              "option_len_spread": {"parent": option_spread(sk.d), "child": option_spread(d)}}
    touched = Touched(item=C.global_id(w.id), condition=w.if_,
                      how=f"realized indirectly ({technique}): {how}; changes the basis of {C.global_id(tc)}")
    feats = {"operator": "flip", "facts_touched_by_kind": kind_counts(X, edits), "n_edits": len(edits),
             "magnitude": scores.get("recall"), "technique": technique}
    T, partial = assemble(ctx, X, "flip", tid, d, sk, "by-construction", detail, new_con, {tc}, "flips", [C.global_id(w.id)],
                          then, touched, feats, "flip")
    return T, partial


def mean_surface_distance_d(sk, d) -> float:
    from .overlap import jaccard
    xs = [1 - jaccard(a["fact"], b["fact"]) for a, b in zip(sk.d["facts"], d["facts"]) if a["id"] not in sk.fixed]
    return sum(xs) / len(xs) if xs else 1.0
