"""revise_card (design 7.3): edit A (the weighing), never F or Q, so that a code-picked different option becomes the verdict.

Code picks the target (balanced by move across the batch; hand-ups, i.e. ask/refuse, capped at 1/3 of targets). gpt-oss
(role `perturber`) re-weights existing considerations or adds ONE that cites existing C facts; policy text goes in
reasoning.weighing. Gate: schema-valid, verdict = target, F and Q identical, Δ_K (considerations whose weight or favors
changed) computed in code and compared with the model's claim, no source narration (R40), no personal names.

Output: C' (Scenario; lineage.parent = C, operator revise_card, tier by-construction, tag `revised-authored`) and a gold
partial written to data/store/partials/revised/<C' id>.yaml (see `build_partial`). W2 pairs (C', restyle(C)'s trace).
"""
from __future__ import annotations

import copy
import json
import re
from collections import Counter

from bench.schema import Case
from bench.schema.pipeline import GoldMap, GPair, Touched

from . import pconfig
from .common import (Ctx, OperatorError, REASON, apply_structure, build_scenario, build_skeleton, bundle, finish_flip_conditions,
                     frame_same, next_id, _s)
from .phi import assert_back_flip, check_count, shuffle_and_renumber

HANDUP = ("ask", "refuse")
PROMPT = "revise_card.v1"

NARRATION = re.compile(
    r"\b(?:the|this|that)\s+(?:source|document|opinion|decision|report|judge|adjudicator|court|tribunal|authors?|text|passage|original(?: case)?)\s+"
    r"(?:emphasi[sz]es?|states?|notes?|argues?|says?|finds?|found|concludes?|reasons?|holds?|writes?|observes?|stresses|treats|weighs|describes|reports)\b"
    r"|\baccording to the (?:source|document|opinion|decision|report|original)\b|\bas the (?:source|document|opinion) (?:puts|notes|states)\b"
    r"|\bin the (?:source|original) (?:document|text|case)\b|\b(?:source|original) (?:reasoning|narrative)\b", re.I)
TITLED = re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Dr|Prof|Judge|Sgt|Capt|Col|Gen|Lt|Cmdr|Adm)\.?\s+[A-Z][a-z]+")
CAPWORD = re.compile(r"(?<![\w{])[A-Z][a-z]{2,}\b")
COMMON_CAP = set("january february march april may june july august september october november december monday tuesday wednesday "
                 "thursday friday saturday sunday".split())


# ------------------------------------------------------------------ target choice
def pick_target(X, rng, tally: Counter | dict | None = None, cap: float | None = None, force: str | None = None) -> dict:
    """Target option != C's choice. Balanced by move over `tally` (move -> count of earlier targets); hand-up targets
    (ask/refuse) keep their running share <= cap when a non-hand-up target exists (else the cap is waived and recorded)."""
    cap = pconfig.get("handup_cap") if cap is None else cap
    tally = Counter(tally or {})
    case = X.case
    opts = {o: v.move for o, v in case.options.items() if o != case.verdict.choice}
    if force:
        if force not in opts:
            raise OperatorError(f"{X.id}: target {force} must be an option other than the case's choice")
        return {"target": force, "move": opts[force], "cap_waived": False, "forced": True}
    if not opts:
        raise OperatorError(f"{X.id}: no option other than the verdict")
    total, hand = sum(tally.values()), tally["ask"] + tally["refuse"]
    allowed = dict(opts)
    nonhand = {o: m for o, m in opts.items() if m not in HANDUP}
    waived = False
    if (hand + 1) / (total + 1) > cap:
        if nonhand:
            allowed = nonhand
        else:
            waived = True
    moves = sorted(set(allowed.values()))
    least = min(tally[m] for m in moves)
    move = rng.choice([m for m in moves if tally[m] == least])
    target = rng.choice(sorted(o for o, m in allowed.items() if m == move))
    return {"target": target, "move": move, "cap_waived": waived, "forced": False,
            "tally": dict(tally), "handup_share_before": round(hand / total, 3) if total else 0.0}


def target_tally(store) -> Counter:
    """Moves of the targets of every revise_card scenario already in the store (batch balance across invocations)."""
    t: Counter = Counter()
    for s in store.scenarios():
        if s.lineage.operator == "revise_card":
            t[s.case.options[s.case.verdict.choice].move] += 1
    return t


# ------------------------------------------------------------------ text validation (R40, names)
def check_text(strings: dict[str, str], known: str) -> None:
    known_l = set(re.findall(r"[a-z]+", known.lower()))
    bad = []
    for k, s in strings.items():
        if NARRATION.search(s):
            bad.append(f"{k}: source narration ({NARRATION.search(s).group(0)!r})")
        m = TITLED.search(s)
        names = [m.group(0)] if m else []
        for mm in CAPWORD.finditer(s):
            w = mm.group(0)
            pre = s[:mm.start()].rstrip()
            if (not pre or pre[-1] in ".!?:;\"'(") or w.lower() in known_l or w.lower() in COMMON_CAP:
                continue
            names.append(w)
        if names:
            bad.append(f"{k}: possible personal name or new proper noun {names[:3]}")
    if bad:
        raise ValueError("rejected text: " + "; ".join(bad) + ". No source narration and no personal names; name roles, not people.")


# ------------------------------------------------------------------ delta K and invariants
def delta_k(C, d: dict) -> dict:
    old = {c.id: c for c in C.considerations}
    changed, details = [], {}
    for c in d["considerations"]:
        o = old.get(c["id"])
        if o is None:
            continue
        dw = o.weight != c["weight"]
        df = set(o.favors) != set(c["favors"])
        dr = sorted(o.rules_out or []) != sorted(c.get("rules_out") or [])
        if dw or df or dr:
            changed.append(c["id"])
            details[c["id"]] = {"weight": [o.weight, c["weight"]], "favors": [sorted(o.favors), sorted(c["favors"])]}
    added = [c["id"] for c in d["considerations"] if c["id"] not in old]
    return {"changed": changed, "added": added, "details": details}


FQ_KEYS = ("setting", "decider", "agent", "agent_role", "situation", "question", "options", "facts")


def assert_fq_unchanged(C: Case, d: dict) -> None:
    """F and Q identical (design 7.3). Compared on the dumped dicts."""
    a = C.dump()
    bad = [k for k in FQ_KEYS if a[k] != d[k]]
    if bad:
        raise OperatorError(f"revise_card changed F/Q fields {bad}: this is a bug, F and Q must be identical")


# ------------------------------------------------------------------ the operator
def revise_card(X, store, rng, *, tally=None, target: str | None = None):
    C = X.case
    pt = pick_target(X, rng, target_tally(store) if tally is None else tally, force=target)
    tgt, move = pt["target"], pt["move"]
    tries = pconfig.get("perturb_tries")
    ctx = Ctx("revise_card", X, store, rng)
    ctx.code_step("revise_card.pick_target", f"target {tgt} (move {move}) picked in code, seeded, balanced by move; hand-up cap", pt)
    sk = build_skeleton(X, [], rng, remap_prose=False)               # identity: no fact changes
    shuffle_seed = rng.getrandbits(32)
    n_wc = len(C.flip_conditions.would_change)
    known = json.dumps(C.dump(), ensure_ascii=False)
    orig_ids = {w.id for w in C.flip_conditions.would_change}

    dropped = [w.id for w in C.flip_conditions.would_change if w.then == tgt]
    need = len(dropped)
    kept_back = any(w.then == C.verdict.choice for w in C.flip_conditions.would_change if w.then != tgt)
    if kept_back:
        back_note = f"One kept item already points back to {C.verdict.choice}."
    elif need:
        back_note = f"No kept item points back to {C.verdict.choice}: at least one new_would_change entry must have `then` {C.verdict.choice}."
    else:
        back_note = (f"No item points back to {C.verdict.choice}: re-point one kept item with \"flip\": {{\"<id>\": {{\"then\": "
                     f"\"{C.verdict.choice}\", \"if\": ..., \"why\": ...}}}} (and send no new_would_change).")
    user = (f"TARGET: {tgt} ({C.options[tgt].do}). The case's current verdict is {C.verdict.choice}.\n"
            f"The case has {n_wc} would_change items. The system drops the ones whose `then` is {tgt} ({', '.join(dropped) or 'none'}), "
            f"so send EXACTLY {need} new_would_change entr{'y' if need == 1 else 'ies'} (each with `then` an option other than {tgt}); "
            f"the final list then has {n_wc} items. {back_note}\n\nCASE:\n"
            + json.dumps(bundle(sk.d, {"fq", "a"}) | {"flip_then": {w.id: w.then for w in C.flip_conditions.would_change}},
                         indent=1, ensure_ascii=False))
    meta = {}

    def validate(out):
        d = copy.deepcopy(sk.d)
        cons = out.get("considerations") or {}
        if not isinstance(cons, dict):
            raise ValueError("considerations must be an object keyed by consideration id")
        for cid, u in cons.items():
            if cid not in {c["id"] for c in d["considerations"]} or not isinstance(u, dict):
                raise ValueError(f"considerations.{cid}: not an existing consideration id with an object value")
            if set(u) - {"weight", "favors", "rules_out", "why"}:
                raise ValueError(f"considerations.{cid}: only weight, favors, rules_out and why may change (facts and equity are fixed)")
        # existing considerations: weight / favors / rules_out / why
        for c in d["considerations"]:
            u = cons.get(c["id"]) or {}
            if "why" in u:
                c["why"] = _s(u["why"], f"considerations.{c['id']}.why")
            for k in ("weight", "favors"):
                if k in u:
                    c[k] = u[k]
            if "rules_out" in u:
                if u["rules_out"]:
                    c["rules_out"] = u["rules_out"]
                else:
                    c.pop("rules_out", None)
        nc = out.get("new_consideration")
        fresh = {"new_considerations": [nc]} if nc else {}
        if nc:
            if not isinstance(nc, dict) or not nc.get("facts") or not set(nc["facts"]) <= {f["id"] for f in d["facts"]}:
                raise ValueError("new_consideration must cite at least one existing fact id in `facts`")
            nc["why"] = _s(nc.get("why"), "new_consideration.why")
        orig_con = [c["id"] for c in d["considerations"]]
        apply_structure(d, {"decisive": out.get("decisive"), **fresh}, tgt, orig_con)
        for c in d["considerations"]:
            if c["weight"] == "bar" and tgt in (c.get("rules_out") or []):
                raise ValueError(f"{c['id']} is a bar that rules out the target {tgt}")
        dk = delta_k(C, d)
        if not dk["changed"] and not dk["added"]:
            raise ValueError("nothing changed: re-weight at least one existing consideration or add one")
        claimed = out.get("changed")
        if not isinstance(claimed, list) or set(claimed) != set(dk["changed"]):
            raise ValueError(f"`changed` must list exactly the existing considerations whose weight, favors or rules_out you changed; "
                             f"you claimed {claimed!r} but the actual changes are {dk['changed']} (details {dk['details']})")
        for cid in dk["changed"]:
            if cid not in cons or "why" not in cons[cid]:
                raise ValueError(f"give a rewritten `why` for changed consideration {cid}")
        # reasoning
        r, ro = d["reasoning"], out.get("reasoning") or {}
        for k in REASON:
            r[k] = _s(ro.get(k), f"reasoning.{k}")
        tw = ro.get("tempting_wrong") or {}
        if tw.get("option") not in d["options"] or tw.get("option") == tgt:
            raise ValueError("reasoning.tempting_wrong.option must be an option id other than the target")
        r["tempting_wrong"] = {"option": tw["option"], "pull": _s(tw.get("pull"), "tempting_wrong.pull"),
                               "why_wrong": _s(tw.get("why_wrong"), "tempting_wrong.why_wrong")}
        rj = ro.get("rejected") or {}
        if not isinstance(rj, dict) or tgt in rj or not set(rj) <= set(d["options"]):
            raise ValueError("reasoning.rejected must map option ids other than the target to reasons")
        r["rejected"] = {k: _s(v, f"reasoning.rejected.{k}") for k, v in rj.items()}
        # flip conditions (Φ)
        fc = d["flip_conditions"]
        for wid, u in (out.get("flip") or {}).items():
            w = next((w for key in ("would_change", "would_not_change", "watch_for") for w in fc.get(key, []) if w["id"] == wid), None)
            if w is None or not isinstance(u, dict):
                raise ValueError(f"flip.{wid}: not an existing flip item")
            if "then" in u:
                if "then" not in w or u["then"] not in d["options"] or u["then"] == tgt:
                    raise ValueError(f"flip.{wid}.then must be an option id other than the target, on a would_change item")
                w["then"] = u["then"]
            key = "what" if "what" in w else "if"
            if key in u:
                w[key] = _s(u[key], f"flip.{wid}.{key}")
            if "why" in u:
                w["why"] = _s(u["why"], f"flip.{wid}.why")
        finish_flip_conditions(d, out, tgt, C.verdict.choice, fired=None, need_back=True)
        check_count(d, n_wc, tgt)
        new_wc = [w["id"] for w in d["flip_conditions"]["would_change"] if w["id"] not in orig_ids]
        d["lesson"] = _s(out.get("lesson"), "lesson")
        d["limits"] = _s(out.get("limits"), "limits")
        d["verdict"]["basis"] = "recommended"
        mp = shuffle_and_renumber(d, shuffle_seed)
        assert_back_flip(d, C.verdict.choice, tgt)
        Case.model_validate({**d, "id": X.id})
        # text rules: only strings the model wrote
        written = {f"c.{c['id']}": c["why"] for c in d["considerations"]}
        written.update({f"reasoning.{k}": v for k, v in r.items() if isinstance(v, str)})
        written.update({"tw.pull": r["tempting_wrong"]["pull"], "tw.why": r["tempting_wrong"]["why_wrong"],
                        "lesson": d["lesson"], "limits": d["limits"], "summary": _s(out.get("summary"), "summary")})
        written.update({f"rejected.{k}": v for k, v in r["rejected"].items()})
        written.update({f"{w['id']}": w["if"] + " " + w["why"] for w in d["flip_conditions"]["would_change"]})
        if nc and nc.get("equity"):
            written["new.equity"] = str(nc["equity"]).replace("_", " ")
        check_text(written, known)
        assert_fq_unchanged(C, d)
        meta.update(dk=dk, summary=written["summary"], authored_wc=[mp[i] for i in new_wc], mapping=mp)
        return d

    d, _ = ctx.ask("perturber", "revise", PROMPT, user, validate, tries=tries, step_id="revise_card.revise")
    dk = meta["dk"]
    ctx.prov.fields.update({"case.considerations": "revise_card.revise", "case.reasoning": "revise_card.revise",
                            "case.verdict": "revise_card.revise", "case.flip_conditions": "revise_card.revise",
                            "case.lesson": "revise_card.revise", "case.limits": "revise_card.revise"})
    ctx.prov.authored = sorted({"case.considerations", "case.reasoning", "case.verdict", "case.flip_conditions", "case.lesson",
                                "case.limits"})
    tid = next_id(store, X.family, "revise_card")
    detail = {"target": tgt, "target_move": move, "parent_choice": C.verdict.choice,
              "parent_move": C.options[C.verdict.choice].move, "pick": pt,
              "delta_k": {"changed": [C.global_id(i) for i in dk["changed"]], "added": [f"{tid}/{i}" for i in dk["added"]],
                          "details": {C.global_id(k): v for k, v in dk["details"].items()}},
              "summary": meta["summary"], "authored_would_change": [f"{tid}/{i}" for i in meta["authored_wc"]],
              "prompt": PROMPT, "judgments": "stipulated, not an oracle's (R54)"}
    T = build_scenario(X, ctx, "revise_card", tid, d, "by-construction", sk, detail)
    T.tags = sorted(set(T.tags) | {"revised-authored"} | ({"flip-conditions-authored"} if meta["authored_wc"] else set()))
    T.basis = f"revised by revise_card from {X.id}; target {tgt} stipulated, not source-endorsed"
    T.provenance.authored = ctx.prov.authored
    partial = build_partial(X, T, tgt, dk, meta["summary"], ctx)
    return T, partial


def build_partial(X, T, tgt: str, dk: dict, summary: str, ctx) -> dict:
    """Gold partial for pair (W2): the card is C' (case_scenario); the trace is restyle(C)'s, which pair substitutes for the
    placeholder `trace_scenario` (= C; restyle keeps every id, so replacing the scenario prefix of the live ids is exact).
    Maps are written from the CARD side C' (case) to C (live)."""
    C, Cp = X.case, T.case
    g = GoldMap(matched=[GPair(live=C.global_id(f.id), case=Cp.global_id(f.id)) for f in C.facts])
    cm = GoldMap()
    for c in C.considerations:
        (cm.corresponding if c.id in dk["changed"] else cm.matched).append(GPair(live=C.global_id(c.id), case=Cp.global_id(c.id)))
    cm.case_only = [Cp.global_id(i) for i in dk["added"]]
    live = sorted([x.live for x in g.matched + g.corresponding] + [x.live for x in cm.matched + cm.corresponding])
    case_side = sorted([x.case for x in cm.matched + cm.corresponding] + cm.case_only)
    if live != sorted([C.global_id(f.id) for f in C.facts] + [C.global_id(c.id) for c in C.considerations]) or \
            case_side != sorted(Cp.global_id(c.id) for c in Cp.considerations):
        raise OperatorError("revise_card gold maps incomplete (bug)")
    first = (dk["changed"] or dk["added"])[0]
    touched = Touched(item=(C.global_id(first) if first in dk["changed"] else Cp.global_id(first)), condition=summary,
                      how=("re-weighted " + ", ".join(dk["changed"]) if dk["changed"] else "") +
                          (" and " if dk["changed"] and dk["added"] else "") + ("added " + ", ".join(dk["added"]) if dk["added"] else ""))
    partial = dict(intent="revised", arm="revised", case_scenario=T.id, trace_scenario=X.id, frame=frame_same(),
                   options_map={C.global_id(o): Cp.global_id(o) for o in C.options}, fact_map=g, consideration_map=cm, governs=True,
                   relation="follows", via=None, choice=C.global_id(tgt), gold_tier="by-construction", touched=touched,
                   tags=["revised-authored"],
                   distance_features={"operator": "revise_card", "source_card": X.id, "revised_card": T.id,
                                      "target_choice": tgt, "target_option": Cp.global_id(tgt), "target_move": Cp.options[tgt].move,
                                      "parent_choice": C.verdict.choice,
                                      "delta_k": T.lineage.detail["delta_k"], "n_changed": len(dk["changed"]),
                                      "n_added": len(dk["added"]),
                                      "trace_scenario_is_placeholder": "pair substitutes restyle(C) for trace_scenario"},
                   provenance=T.provenance)
    return partial
