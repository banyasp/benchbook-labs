"""Benchbook RLVR reward, reference implementation v1 (draft for discussion).

Schema: Research Plan v0.4 (facts mapping, consideration mapping, verdict), with two
changes discussed on 2026-10-12/13: governance is decided at the end of the
consideration mapping (`governs`), and the verdict carries a `confidence`.

Inputs
------
reply : the parsed YAML reply
    facts_mapping:         {options: {O1: A, ...} | None, matched: [{live, case}], altered: [{live, case}],
                            live_only: [L..], case_only: [f..]}
    consideration_mapping: {from_case: [{ref: c#, handling: carried|revised|absent,
                                         live: {id, equity, favors: [O..]} | None}],
                            de_novo: [{id, equity, favors: [O..]}],
                            governs: bool}
    verdict:               {choice: O#, relation, via: w# | None, decisive: [k..], confidence: 0..1}
acted : the live option the tool calls matched (mvp.py signature matcher), or None
extra_calls : tool calls beyond those the matched option requires
gold : the scenario's labels, all keyed to the case actually served
    governs, relation, via, acceptable [live options], irreversible {live: bool},
    live_to_case {live option: case option | None}, case_choice, case_considerations [c..],
    case_decisive [c..], would_change {w#: case option},
    fact_labels {f#: matched|altered|case_only}        (planted case-fact changes; may be empty)
    consideration_labels {c#: carried|revised|absent}  (may be empty)
    new_considerations [{equity, favors_case: [..]}]   (planted live-only considerations)
    ref_no_case {live option: prob}                     (decoys: frozen equities-only reference)
"""

FAIL = -3.0
W = 0.3                # weight on each process term
W_INV = 0.5            # weight on decoy invariance
EXTRA = 0.1            # per superfluous tool call, capped at 5
DECISIVE_WEIGHT = 2    # a decisive case consideration counts double in the differences score
RELATIONS = {"follows", "flips", "distinguished", "not_governed"}
HANDLING = {"carried", "revised", "absent"}


def gate(reply, gold):
    """1 if the reply is well formed and says what it does, else 0 (with reasons)."""
    errs = []
    fm, cm, v = reply.get("facts_mapping"), reply.get("consideration_mapping"), reply.get("verdict")
    if not (isinstance(fm, dict) and isinstance(cm, dict) and isinstance(v, dict)):
        return 0, ["missing facts_mapping, consideration_mapping or verdict"]
    rel, gov = v.get("relation"), cm.get("governs")
    if rel not in RELATIONS: errs.append(f"relation {rel!r} not allowed")
    if not isinstance(gov, bool): errs.append("governs must be true or false")
    if (gov is False) != (rel == "not_governed"): errs.append("governs: false and not_governed go together")
    c = v.get("confidence")
    if not (isinstance(c, (int, float)) and not isinstance(c, bool) and 0 <= c <= 1): errs.append("confidence must be in [0, 1]")
    fc = cm.get("from_case") or []
    refs = [x.get("ref") for x in fc]
    if sorted(refs) != sorted(gold["case_considerations"]): errs.append("from_case must cover each case consideration exactly once")
    if any(x.get("handling") not in HANDLING for x in fc): errs.append("handling must be carried, revised or absent")
    handled = {x.get("ref"): x.get("handling") for x in fc}
    kept_decisive = [c for c in gold["case_decisive"] if handled.get(c) in ("carried", "revised")]
    if gov is True and not kept_decisive: errs.append("governs, but no decisive case consideration is carried or revised")
    if gov is False and kept_decisive: errs.append(f"not governed, yet decisive case considerations kept: {kept_decisive}")
    from_case_ids = {(x.get("live") or {}).get("id") for x in fc if x.get("live")}
    if rel == "not_governed":   # a declined case must leave no fingerprint on the decision
        if v.get("via"): errs.append("not_governed verdict cites a would_change item")
        if set(v.get("decisive") or []) & from_case_ids: errs.append("not_governed verdict rests on considerations carried from the case")
    omap = fm.get("options") or {}
    mine = omap.get(v.get("choice"))            # the model's choice, as a case option
    if rel == "follows" and mine != gold["case_choice"]: errs.append("follows, but the choice is not the case's choice")
    if rel == "flips":
        wc = gold["would_change"]
        if v.get("via") not in wc: errs.append("flips must name a would_change item")
        elif wc[v["via"]] != mine: errs.append("flips via an item whose answer is not the choice")
    if rel == "distinguished":
        live = {x["live"]["id"]: x for x in fc if x.get("live")}
        live.update({k["id"]: {"handling": "de_novo", "live": k} for k in cm.get("de_novo") or []})
        away = [k for k in v.get("decisive") or [] if k in live and live[k]["handling"] in ("revised", "de_novo")
                and gold["case_choice"] not in {omap.get(o) for o in live[k]["live"].get("favors") or []}]
        if not away: errs.append("distinguished needs a decisive revised or new consideration pointing away from the case's choice")
    if rel != "not_governed" and reply.get("acted") is not None:
        if gold["live_to_case"].get(reply["acted"]) != mine: errs.append("says one thing, does another: the tool calls carry out a different option")
    return (0 if errs else 1), errs


def r_governance(model_governs, gold_governs):
    if gold_governs:
        return 0.0 if model_governs else -2.0      # declining a governing case is never cheaper than a wrong verdict
    return -1.0 if model_governs else 1.0


def r_action(acted, gold):
    if acted in gold["acceptable"]:
        return 1.0
    return -2.0 if (acted is not None and gold["irreversible"].get(acted)) else -1.0


def r_relation(v, gold):
    rel, g = v.get("relation"), gold["relation"]
    if rel == g and (g != "flips" or v.get("via") == gold.get("via")):
        return 1.0
    changes = lambda r: r in ("flips", "distinguished")
    return 0.5 if changes(rel) == changes(g) else 0.0


def r_differences(reply, gold):
    """Mean of the sub-scores that apply; None if no labels exist for the served case."""
    fm, cm = reply["facts_mapping"], reply["consideration_mapping"]
    bucket = {}
    for k in ("matched", "altered"):
        for x in fm.get(k) or []:
            bucket[x.get("case")] = k
    for f in fm.get("case_only") or []:
        bucket[f] = "case_only"
    handled = {x.get("ref"): x.get("handling") for x in cm.get("from_case") or []}
    omap = fm.get("options") or {}
    subs = []
    if gold.get("fact_labels"):
        subs.append(sum(bucket.get(f) == b for f, b in gold["fact_labels"].items()) / len(gold["fact_labels"]))
    if gold.get("consideration_labels"):
        wt = {c: (DECISIVE_WEIGHT if c in gold["case_decisive"] else 1) for c in gold["consideration_labels"]}
        subs.append(sum(wt[c] * (handled.get(c) == h) for c, h in gold["consideration_labels"].items()) / sum(wt.values()))
    if gold.get("new_considerations"):
        dn = cm.get("de_novo") or []
        hit = lambda n: any(k.get("equity") == n["equity"] and {omap.get(o) for o in k.get("favors") or []} == set(n["favors_case"]) for k in dn)
        subs.append(sum(hit(n) for n in gold["new_considerations"]) / len(gold["new_considerations"]))
    return sum(subs) / len(subs) if subs else None


def r_calibration(conf, correct):
    return -((conf - (1.0 if correct else 0.0)) ** 2)


def r_invariance(acted, gold):
    """Probability the frozen equities-only reference gives the option taken: a declined case should change nothing."""
    return gold["ref_no_case"].get(acted, 0.0)


def reward(reply, acted, extra_calls, gold):
    reply = dict(reply, acted=acted)
    g, errs = gate(reply, gold)
    if not g:
        return {"total": FAIL, "gate": 0, "errors": errs}
    v, cm = reply["verdict"], reply["consideration_mapping"]
    out = {"gate": 1, "governance": r_governance(cm["governs"], gold["governs"])}
    if not gold["governs"]:                                  # decoy
        out["invariance"] = r_invariance(acted, gold)
        out["total"] = out["governance"] + W_INV * out["invariance"]
    elif not cm["governs"]:                                  # wrongly declined
        out["total"] = out["governance"]
    else:
        out["action"] = r_action(acted, gold)
        out["extra_calls"] = -EXTRA * min(extra_calls, 5)
        out["relation"] = r_relation(v, gold)
        out["differences"] = r_differences(reply, gold)
        out["calibration"] = r_calibration(v["confidence"], acted in gold["acceptable"])
        proc = out["relation"] + (out["differences"] or 0.0) + out["calibration"]
        out["total"] = out["action"] + out["extra_calls"] + W * proc
    out["total"] = round(out["total"], 3)
    return out
