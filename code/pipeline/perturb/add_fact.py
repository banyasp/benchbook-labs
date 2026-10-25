"""add_fact: one new fact the card never mentions; T's verdict from an INDEPENDENT solve that sees only T's F and Q.

Isolation: the solver's messages are built by `solver_messages(case_dict)` from T's facts and question frame only
(no ids that reveal the operator, no considerations, verdict, flip conditions, prose of A, parent id, or which fact is new).
Gold: tier model-solved; relation follows if the solver's choice is C's choice (options map is the identity on ids),
else distinguished. Fact map: the new fact live_only, the rest matched. Consideration map from the composed answer.
"""
from __future__ import annotations

import copy
import json
import time
from pathlib import Path

from bench.schema import Case
from bench.schema.pipeline import Touched

from .common import (_transcript, OperatorError, complete, model_of, parse_json, sha256_obj, Ctx, Edit, KINDS, STATUSES, apply_structure, apply_text, assemble, build_skeleton, bundle,
                     finish_flip_conditions, next_id, option_spread)
from .overlap import jaccard, overlap

MODES = ("relevant", "ambiguous", "background")
MIN_KEEP = 0.4           # the restyled new fact must keep this share of the proposal's content words
MIN_SURFACE = 0.25

TASK_FQ = """TASK (restyle F and Q): the scenario below has one more fact than before. Lightly restyle the whole scenario so the
facts and the question frame read as one coherent text: new wording and register for setting, decider, agent, situation,
question, options and every fact, keeping each fact's content, kind and status and every id. Keep the new fact's content
fully (its wording may change). The situation must mention everything the facts say and nothing they do not. Reply with
{"setting", "decider", "agent", "situation", "question", "options": {"O1": "..."}, "facts": {"F1": "..."}}."""

TASK_A = """TASK (compose the answer): the scenario below (facts F and question frame Q) is a modified version of a parent
scenario whose worked answer is in the bundle (its ids already follow this scenario's numbering; new fact: {new}).
An independent analyst, who saw only this scenario, chose {choice} ("{choice_do}"). That choice is FIXED: write the answer
record for this scenario that reaches it. The parent chose {c_choice}.
- Considerations: give each existing consideration's new "why" as {"C1": {"why": "..."}}; if the new fact changes one's facts,
  favors, weight or rules_out, include those fields (use the fact ids given); {"drop": true} removes one that no longer applies.
  Add "new_considerations" (facts, equity, favors, weight, why) when the new fact brings an interest into play (the analyst's
  considerations are below). "decisive": ids that decide for {choice}.
- "touches": {"consideration": <id of the PARENT consideration the new fact bears on, or null if it bears on none>,
  "condition": "the condition in the parent's weighing it bears on, in words, or why it is irrelevant", "how": "one sentence"}.
- Reasoning: rewrite every field so it reaches {choice}; "tempting_wrong": {"option": <option id other than {choice}>, "pull",
  "why_wrong"}; "rejected": {<option id other than {choice}>: why}. Mention the new fact where it matters or note that it does not.
- Flip items: restyle each ("flip": {"flip1": {"if", "why"}, "noflip1": {"if","why"}, "watch1": {"what","why"}}); their "then"
  values are handled by the system. {back}
- lesson and limits: rewrite so they fit. Prose references use ids from the bundle ({F3}, {C2}, {O1}).
- Do not change facts or the question frame (they are fixed in this task); reply only with the answer parts."""


def solver_messages(d: dict) -> list[dict]:
    """The independent solver's whole input: T's frame, options and facts. Nothing of the parent, nothing of A."""
    sysm = (Path(__file__).parent / "prompts" / "solve_independent.md").read_text()
    opts = "\n".join(f"{k}: {o['do']}  [move: {o['move']}{'; irreversible' if o.get('irreversible') else ''}"
                     f"{'; to: ' + o['to'] if o.get('to') else ''}]" for k, o in d["options"].items())
    facts = "\n".join(f"{f['id']} [{f['kind']}, {f['status']}]: {f['fact']}" for f in d["facts"])
    user = (f"SETTING: {d['setting']}\nDECIDER: {d['decider']}\nAGENT: {d['agent']} (role: {d['agent_role']})\n\n"
            f"SITUATION: {d['situation']}\n\nQUESTION: {d['question']}\n\nOPTIONS:\n{opts}\n\nFACTS:\n{facts}")
    return [{"role": "system", "content": sysm}, {"role": "user", "content": user}]


def add_fact(X, store, rng, *, mode: str | None = None):
    C = X.case
    ctx = Ctx("add_fact", X, store, rng)
    mode = mode or rng.choices(MODES, [0.5, 0.25, 0.25])[0]

    # ---- stage A: propose the fact
    user = (f"MODE: {mode}\n\nQUESTION: {C.question}\nOPTIONS: " + "; ".join(f"{k}: {o.do}" for k, o in C.options.items())
            + "\n\nFACTS:\n" + "\n".join(f"{f.id} [{f.kind}, {f.status}]: {f.fact}" for f in C.facts)
            + "\n\nCONSIDERATIONS:\n" + "\n".join(f"{c.id} ({c.equity}, favors {','.join(c.favors)}): {c.why}" for c in C.considerations)
            + "\n\nFLIP CONDITIONS ALREADY COVERED:\n"
            + "\n".join(w.if_ for w in C.flip_conditions.would_change + C.flip_conditions.would_not_change)
            + "\n" + "\n".join(w.what for w in C.flip_conditions.watch_for))
    covered = [f.fact for f in C.facts] + [w.if_ for w in C.flip_conditions.would_change + C.flip_conditions.would_not_change] \
        + [w.what for w in C.flip_conditions.watch_for]

    def validate_a(out):
        text = out.get("text")
        if not isinstance(text, str) or len(text.split()) < 4:
            raise ValueError("text must be a sentence or two")
        if out.get("kind") not in KINDS or out.get("status") not in STATUSES:
            raise ValueError(f"kind must be one of {KINDS}, status one of {STATUSES}")
        for c in covered:
            if not overlap(text, c)["pass"] and len(c.split()) > 3:
                raise ValueError(f"the fact repeats something already covered: `{c}`")
        return out

    prop, _ = ctx.ask("perturber", "propose", "propose_fact", user, validate_a, step_id="add_fact.propose")
    sk = build_skeleton(X, [Edit("add", None, prop["text"].strip(), prop["kind"], prop["status"])], rng)
    new_tid = next(t for t, o in sk.origin.items() if o == "new")
    sk.fixed = set()                                        # the new fact may be lightly restyled with the rest

    # ---- stage B: restyle F and Q (T's F and Q only; A not yet written)
    user = TASK_FQ + "\n\nBUNDLE:\n" + json.dumps(bundle(sk.d, {"fq"}), indent=1, ensure_ascii=False)

    def validate_b(out):
        d = copy.deepcopy(sk.d)
        apply_text(d, out, {"fq"})
        kept = overlap(next(f["fact"] for f in d["facts"] if f["id"] == new_tid), prop["text"])["recall"]
        # overlap(new, if) = recall of `if` tokens (the proposal) in `new` (the rewritten fact)
        if kept < MIN_KEEP:
            raise ValueError("the new fact lost its content in the rewrite; keep it")
        old = {f["id"]: f["fact"] for f in sk.d["facts"]}
        dist = [1 - jaccard(old[f["id"]], f["fact"]) for f in d["facts"] if f["id"] != new_tid]
        if dist and sum(dist) / len(dist) < MIN_SURFACE:
            raise ValueError("restyle the other facts more")
        sp, sp0 = option_spread(d), option_spread(sk.d)
        if sp > max(1.3, sp0 * 1.15):
            raise ValueError(f"options must stay a matched set: longest/shortest word-count ratio is {sp} (original {sp0}); equalize their length")
        return d

    d_fq, _ = ctx.ask("perturber", "restyle_fq", "rewrite", user, validate_b, step_id="add_fact.restyle_fq")

    # ---- stage S: independent solve (sees only d_fq)
    msgs = solver_messages(d_fq)
    opts, fids = set(d_fq["options"]), {f["id"] for f in d_fq["facts"]}

    def validate_s(out):
        if out.get("choice") not in opts:
            raise ValueError(f"choice must be one of {sorted(opts)}")
        cons = out.get("considerations")
        if not isinstance(cons, list) or not cons:
            raise ValueError("considerations must be a non-empty list")
        for c in cons:
            if not set(c.get("facts") or []) <= fids or not set(c.get("favors") or []) <= opts or c.get("weight") not in ("strong", "weak", "bar"):
                raise ValueError("each consideration needs facts (fact ids), favors (option ids), weight strong|weak|bar, why")
        return out

    sol = None
    for attempt in range(3):
        raw = complete("independent_solver", msgs, stage="perturb.add_fact.independent_solve")
        _transcript("add_fact", "independent_solve", "independent_solver", attempt, msgs, raw)
        try:
            sol = validate_s(parse_json(raw))
            break
        except ValueError as e:
            msgs = msgs + [{"role": "assistant", "content": raw}, {"role": "user", "content": f"Rejected: {e}\nResend the complete JSON object."}]
    if sol is None:
        raise OperatorError("independent solver gave no valid reply")
    ctx.prov.step(id="add_fact.solve", operator="perturb", model=model_of("independent_solver"), role="independent_solver",
                  prompt_version="solve_independent", inputs={"messages": sha256_obj(msgs[:2])},
                  params={"sees": "T.F and T.Q only", "attempts": attempt + 1}, ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                  notes="independent solve; never sees C, its answer or which fact is new")
    choice = sol["choice"]
    c_choice = C.verdict.choice
    relation = "follows" if choice == c_choice else "distinguished"

    # ---- stage D: compose T's answer toward the fixed choice
    sk2 = copy.deepcopy(sk)
    sk2.d.update({k: d_fq[k] for k in ("setting", "decider", "agent", "situation", "question")})
    sk2.d["options"] = d_fq["options"]
    sk2.d["facts"] = d_fq["facts"]
    back = (f"The parent's verdict {c_choice} differs from {choice}: add in new_would_change at least one item whose then is "
            f"{c_choice} (what would restore the parent's choice)." if relation == "distinguished" else "")
    user = (TASK_A.replace("{new}", new_tid).replace("{choice}", choice).replace("{choice_do}", d_fq["options"][choice]["do"])
            .replace("{c_choice}", c_choice).replace("{back}", back)
            + "\n\nSCENARIO FACTS AND FRAME (fixed):\n" + json.dumps(bundle(sk2.d, {"fq"}), indent=1, ensure_ascii=False)
            + "\n\nPARENT ANSWER (ids renumbered to this scenario):\n" + json.dumps(bundle(sk2.d, {"a"}), indent=1, ensure_ascii=False)
            + "\n\nINDEPENDENT ANALYST (saw only the scenario):\n" + json.dumps({k: sol.get(k) for k in ("choice", "considerations", "reasoning", "flip")}, indent=1))
    orig_con = [c.id for c in C.considerations]
    holder = {}

    def validate_d(out):
        d = copy.deepcopy(sk2.d)
        apply_text(d, out, {"a"}, free_reasoning=True)
        d["verdict"]["choice"] = choice
        new_con = apply_structure(d, out, choice, orig_con)
        if d["reasoning"]["tempting_wrong"]["option"] == choice:
            raise ValueError("tempting_wrong.option must differ from the verdict option")
        d["reasoning"]["rejected"].pop(choice, None)
        finish_flip_conditions(d, out, choice, c_choice, need_back=(relation == "distinguished"))
        tz = out.get("touches") or {}
        if tz.get("consideration") not in [None] + orig_con:
            raise ValueError("touches.consideration must be a parent consideration id or null")
        Case.model_validate({**d, "id": X.id})
        holder["touches"] = tz
        return d, new_con

    (d, new_con), _ = ctx.ask("perturber", "compose", "rewrite", user, validate_d, step_id="add_fact.compose")
    ctx.prov.fields.update({"case.considerations": "add_fact.compose", "case.reasoning": "add_fact.compose",
                            "case.verdict": "add_fact.solve", "case.facts": "add_fact.restyle_fq"})
    tz = holder["touches"]
    tc = tz.get("consideration")
    touched = Touched(item=C.global_id(tc) if tc else None, condition=tz.get("condition") or "no condition in the parent's weighing",
                      how=f"added fact: {tz.get('how') or prop['text']}") if tc else None
    detail = {"mode_hint": mode, "new_fact": new_tid, "proposal": prop,
              "solver": {"choice": choice, "considerations": sol["considerations"], "reasoning": sol.get("reasoning"),
                         "flip": sol.get("flip"), "raw": raw, "model": model_of("independent_solver")},
              "parent_choice": c_choice, "option_len_spread": {"parent": option_spread(sk.d), "child": option_spread(d)}}
    tid = next_id(store, X.family, "add_fact")
    feats = {"operator": "add_fact", "facts_touched_by_kind": {prop["kind"]: 1}, "n_edits": 1, "magnitude": 1,
             "mode_hint": mode, "bears_on_weighing": bool(tc), "changed_verdict": relation == "distinguished"}
    T, partial = assemble(ctx, X, "add_fact", tid, d, sk, "model-solved", detail, new_con, {tc} if tc else set(), relation, None,
                          choice, touched, feats, "add_fact")
    return T, partial
