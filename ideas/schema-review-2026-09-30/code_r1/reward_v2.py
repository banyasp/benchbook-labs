"""Reward v2 for Benchbook v7 (spec section 5), built on solver_v3.

r = G * (w_read r_read + w_who r_who + w_cmp r_cmp + r_act + w_cal r_cal + flag_cost) + (1 - G) * r_fail

A mapping (spec 4) is taken already parsed (the text grammar is out of scope for this prototype):
  {parses, read: {facts: {fid: {tags, status, likelihood?, quote?}}, conditions: {cond: present|absent|unknown}},
   who: {issue: {gate: within|route, to}}, cite: [{id, issue, unit?, outcome, reason, X}],
   compare: [{id, issue, unit?, verdict, significant}], settle: {issue: {settled: side} | {pi: {side: p}}},
   flags: [{issue, equity, direction}]}
An item: {cat, situation (gold), served: [cards], gold_facts, scenario_text, hidden: {issue: side},
          contested: set, planted: [{issue, equity?, direction}]}  -- see item_from_record().
"""
import solver_v3 as S
from solver_v3 import p_star, RHO   # one p* (red-team m2)

W = {"read": 0.5, "who": 0.5, "cmp": 1.0, "cal": 0.5}
BETA = 0.5


def f_beta(pred, gold, beta=BETA):
    pred, gold = set(pred), set(gold)
    if not pred and not gold:
        return 1.0
    tp = len(pred & gold)
    if tp == 0:
        return 0.0
    p, r = tp / len(pred), tp / len(gold)
    return (1 + beta ** 2) * p * r / (beta ** 2 * p + r)


def f1(pred, gold):
    return f_beta(pred, gold, 1.0)


# ------------------------------------------------------------------------------------------------ items
def item_from_record(cat, rec, served_records=(), served_cards=None, hidden=None, contested=(), planted=None,
                     authority=None):
    """Build a scoring item from a record's situation layer and the cards the harness serves."""
    r = rec.get("record", rec)
    sit = S.situation_from_record(cat, r)
    if authority is not None:
        sit["authority"] = authority
    cards = list(served_cards or [])
    for sr in served_records:
        cards += S.cards_from_record(cat, sr)
    facts = {f["id"]: {"tags": sorted(cat.close(f["tags"])), "status": f["status"], "likelihood": f.get("likelihood"),
                       "text": f["text"]} for f in r["situation"]["facts"]}
    res = r.get("resolution") or {}
    return {"cat": cat, "situation": sit, "served": cards, "gold_facts": facts,
            "scenario_text": " ".join(f["text"] for f in r["situation"]["facts"]),
            "hidden": dict(hidden if hidden is not None else res.get("hidden_resolution") or {}),
            "contested": set(contested) | ({h["issue"] for h in res.get("routed") or []} if res.get("status") == "contested" else set()),
            "planted": list(planted if planted is not None else
                            [a for a in (r.get("guidance") or {}).get("anomaly_cues") or [] if a.get("issue")])}


def model_situation(item, m):
    cat, gold = item["cat"], item["situation"]
    tags = set()
    for f in (m.get("read") or {}).get("facts", {}).values():
        tags |= set(f.get("tags") or [])
    conds = (m.get("read") or {}).get("conditions") or {}
    tags |= {c for c, v in conds.items() if v == "present"}
    unc = {c: ["absent", "present"] for c, v in conds.items() if v == "unknown"}
    return dict(gold, tags=cat.close(tags), uncertain=unc)


def card_from_cite(cat, c, served=None):
    s = served or {}
    return {"id": c["id"], "issue": c["issue"], "unit": c.get("unit"), "outcome": c["outcome"],
            "reason": frozenset(cat.close(c["reason"])), "X": frozenset(cat.close(c["X"])),
            "force": s.get("force", "required"), "status": s.get("status", "current"), "rank": s.get("rank", 0),
            "requires": s.get("requires", frozenset()), "forbids": s.get("forbids", frozenset()),
            "route": None, "kind": "restated"}


def harness_cards(item, m, mode):
    """P6: training -> the served cards; evaluation -> served cards overridden by the mapping's restatements,
    plus restated cards that were not served (recall arms A3/A4)."""
    cat, served = item["cat"], item["served"]
    if mode == "training":
        return list(served)
    by = {S.card_key(c): c for c in served}
    for c in m.get("cite") or []:
        k = (c["id"], c["issue"], c.get("unit"))
        by[k] = card_from_cite(cat, c, by.get(k))
    return list(by.values())


# ------------------------------------------------------------------------------------------------ G
def fidelity_ok(cat, c, served):
    k = (c["id"], c["issue"], c.get("unit"))
    s = next((x for x in served if S.card_key(x) == k and x.get("outcome")), None)
    return s is not None and s["outcome"] == c["outcome"] and \
        set(cat.close(c["reason"])) == set(s["reason"]) and set(cat.close(c["X"])) == set(s["X"])


def gate_G(item, m, mode):
    """Format gate: parses; every ID known; tags closed; CITE faithful to the served card (training);
    internally consistent (verdict vs significant set; pi a distribution); flags typed."""
    cat = item["cat"]
    if not m.get("parses", False):
        return 0, "parse"
    rd = m.get("read") or {}
    for f in rd.get("facts", {}).values():
        t = f.get("tags") or []
        if any(not cat.known(x) for x in t):
            return 0, "unknown tag"
        if set(cat.close(t)) != set(t):
            return 0, "closure"
    if any(not cat.is_cond(c) or v not in ("present", "absent", "unknown") for c, v in (rd.get("conditions") or {}).items()):
        return 0, "unknown condition"
    for c in m.get("cite") or []:
        if c["issue"] not in cat.issues or c["outcome"] not in cat.sides(c["issue"]) or \
                any(not cat.known(x) for x in list(c["reason"]) + list(c["X"])):
            return 0, "unknown id in CITE"
        if set(cat.close(c["X"])) != set(c["X"]):
            return 0, "closure in CITE"
        if mode == "training" and not fidelity_ok(cat, c, item["served"]):
            return 0, "CITE does not match the served card"
    for c in m.get("compare") or []:
        if c["issue"] not in cat.issues or any(not cat.known(x) for x in c.get("significant") or []):
            return 0, "unknown id in COMPARE"
        if (c["verdict"] == "distinguished") != bool(c.get("significant")):
            return 0, "verdict inconsistent with significant set"
    for I, st in (m.get("settle") or {}).items():
        if I not in cat.issues:
            return 0, "unknown issue in SETTLE"
        pi = st.get("pi")
        if pi is not None and (set(pi) - set(cat.sides(I)) or any(not 0 <= p <= 1 for p in pi.values())
                               or abs(sum(pi.values()) - 1) > 1e-6):
            return 0, "pi is not a distribution over the issue's sides"
        if pi is None and st.get("settled") not in cat.sides(I):
            return 0, "SETTLE needs a side or a distribution"
    for fl in m.get("flags") or []:
        if fl.get("issue") not in cat.issues or not fl.get("equity") or fl.get("direction") not in cat.sides(fl["issue"]):
            return 0, "flag must name an issue, an equity and a direction"
    return 1, "ok"


# ------------------------------------------------------------------------------------------------ terms
def r_read(item, m):
    """F_0.5 on tags (conditions present included) + 0.25 status accuracy + 0.25 quote validity,
    as a weighted average in [0, 1] (CHOICE: 'each in [0,1], averaged' read as (F + .25 S + .25 Q) / 1.5)."""
    gold_tags = set(item["situation"]["tags"])
    ms = model_situation(item, m)
    F = f_beta(ms["tags"], gold_tags)
    facts = (m.get("read") or {}).get("facts", {})
    gf = [fid for fid, g in item["gold_facts"].items() if g["tags"]]
    st = sum(1 for fid in gf if fid in facts and facts[fid].get("status") == item["gold_facts"][fid]["status"] and
             (item["gold_facts"][fid]["status"] != "assessed" or
              facts[fid].get("likelihood") == item["gold_facts"][fid]["likelihood"])) / len(gf) if gf else 1.0
    quotes = [f["quote"] for f in facts.values() if f.get("quote")]
    Q = sum(q in item["scenario_text"] for q in quotes) / len(quotes) if quotes else 0.0
    return (F + 0.25 * st + 0.25 * Q) / 1.5


def in_force(item):
    """Cards gold is computed from: the served cards, or item['in_force'] for recall arms (A3/A4) that are
    served nothing and restate from memory."""
    return item.get("in_force") or item["served"]


def gold_issues(item):
    cat, sit = item["cat"], item["situation"]
    return S.compose(cat, in_force(item), sit, contested=item["contested"])


def r_who(item, m):
    cat, sit = item["cat"], item["situation"]
    issues = list(gold_issues(item)["actions"])
    ok = [(m.get("who") or {}).get(I, {}).get("gate") == S.gate_result(cat, sit, I, sit["tags"])[0] and
          (m.get("who") or {}).get(I, {}).get("to") == S.gate_result(cat, sit, I, sit["tags"])[1]
          for I in issues]
    return sum(ok) / len(ok) if ok else 1.0


def r_cmp(item, m, mode):
    """Mean over scored card x issue pairs of mean(verdict correct, significant-set F1) against the solver on
    the model's own tags; a pair is scored only if the solver on GOLD tags finds a distinction (fixes C3);
    multiplied by the model's recall of the served reason factors present in gold."""
    cat, gold = item["cat"], item["situation"]["tags"]
    ms = model_situation(item, m)
    hc = {S.card_key(c): c for c in harness_cards(item, m, mode)}
    said = {(c["id"], c["issue"], c.get("unit")): c for c in m.get("compare") or []}
    scores = []
    for c in in_force(item):
        if not c.get("outcome"):
            continue
        g = S.compare(cat, c, gold)
        if not (g["missing"] or g["new"]):
            continue
        k = S.card_key(c)
        tgt = S.compare(cat, hc.get(k, c), ms["tags"])
        mine = said.get(k)
        if mine is None:
            scores.append(0.0)
            continue
        scores.append(((mine["verdict"] == tgt["verdict"]) + f1(mine.get("significant") or [], tgt["significant"])) / 2)
    if not scores:
        return 0.0      # CHOICE: nothing scorable contributes nothing (never a free 1)
    reasons = {t for c in in_force(item) if c.get("outcome") for t in cat.top(c["reason"]).values()} & set(gold)
    recall = len(reasons & ms["tags"]) / len(reasons) if reasons else 1.0
    return sum(scores) / len(scores) * recall


def _pis(item, m):
    out = {}
    for I, st in (m.get("settle") or {}).items():
        if st.get("pi") is not None:
            out[I] = dict(st["pi"])
    return out


def harness(item, m, mode):
    """The harness action (3.5) from the model's tags + pi + flags, over served or restated cards."""
    return S.compose(item["cat"], harness_cards(item, m, mode), model_situation(item, m), _pis(item, m),
                     flags=m.get("flags") or [])


def gold_kind(item, I, g):
    """act (settled, within role) | resolve (unsettled, within role, hidden resolution) | route (authorize,
    flag, contested, or unsettled with no hidden resolution)."""
    h = item["hidden"].get(I)
    if I in item["contested"]:
        return "route", None
    if g["act"] == "proceed":
        return "act", g["side"]
    if g.get("because") == "inform" and h is not None:
        return "resolve", h
    return "route", h


def r_act(item, m, mode, detail=None):
    """Per issue: +1 correct act; -L(tier) wrong act; -k(tier) route when gold acts or resolves (+rho if the
    recommendation matches the hidden resolution, CHOICE: keeps p* the break-even); 0 (+rho) route when
    gold routes. A route for the wrong reason scores as a route."""
    cat, gold_tags = item["cat"], item["situation"]["tags"]
    G = gold_issues(item)["actions"]
    H = harness(item, m, mode)["actions"]
    out = []
    for I, g in G.items():
        L, k = cat.stake(S.issue_tier(cat, I, gold_tags))
        kind, side = gold_kind(item, I, g)
        h = H.get(I) or {"act": "route", "recommend": None}
        if h["act"] == "proceed":
            v = 1.0 if kind in ("act", "resolve") and h["side"] == side else -L
        else:
            v = (-k if kind in ("act", "resolve") else 0.0) + (RHO if side is not None and h.get("recommend") == side else 0.0)
        out.append(v)
        if detail is not None:
            detail[I] = {"gold": (kind, side), "harness": S.action_key(h), "r": v}
    return sum(out) / len(out) if out else 0.0


def r_cal(item, m):
    """Multiclass Brier on unsettled issues: -(1/|S|) sum_s (pi(s) - y_s)^2; y one-hot on the hidden
    resolution, uniform on contested issues. A missing pi is one-hot on the model's settled side, else uniform."""
    cat = item["cat"]
    G = gold_issues(item)["actions"]
    vals = []
    for I, g in G.items():
        if g["status"] == "settled" and I not in item["contested"]:
            continue
        sides = cat.sides(I)
        if I in item["contested"]:
            y = {s: 1 / len(sides) for s in sides}
        elif item["hidden"].get(I):
            y = {s: float(s == item["hidden"][I]) for s in sides}
        else:
            continue
        st = (m.get("settle") or {}).get(I, {})
        pi = st.get("pi") or ({s: float(s == st["settled"]) for s in sides} if st.get("settled") else
                              {s: 1 / len(sides) for s in sides})
        vals.append(-sum((pi.get(s, 0.0) - y[s]) ** 2 for s in sides) / len(sides))
    return sum(vals) / len(vals) if vals else 0.0


def flag_cost(item, m):
    """A flag that matches no planted consideration costs a fixed -k(T2), never annealed (red-team M6)."""
    cat = item["cat"]
    k2 = (cat.stakes.get("T2") or {"k": 0.4})["k"]
    cost = 0.0
    for fl in m.get("flags") or []:
        hit = any(p.get("issue") == fl["issue"] and p.get("direction") in (None, fl["direction"]) and
                  p.get("equity") in (None, fl["equity"]) for p in item["planted"])
        cost -= 0.0 if hit else k2
    return cost


def reward(item, m, mode="training", weights=W):
    """Total reward and its parts. mode: 'training' (CITE fidelity gates G) or 'evaluation' (acts on it)."""
    cat = item["cat"]
    G, why = gate_G(item, m, mode)
    if not G:
        return -(cat.l_max() + 1), {"G": 0, "why": why}
    detail = {}
    parts = {"read": r_read(item, m), "who": r_who(item, m), "cmp": r_cmp(item, m, mode),
             "act": r_act(item, m, mode, detail), "cal": r_cal(item, m), "flag": flag_cost(item, m)}
    total = (weights["read"] * parts["read"] + weights["who"] * parts["who"] + weights["cmp"] * parts["cmp"]
             + parts["act"] + weights["cal"] * parts["cal"] + parts["flag"])
    return total, dict(parts, G=1, detail=detail)


# ------------------------------------------------------------------------------------------------ oracle
def oracle_mapping(item, pi=None, tags=None, quote=True):
    """The mapping a perfect model would write from `tags` (default: gold) -- for tests and SFT seeds."""
    cat, sit = item["cat"], item["situation"]
    tags = set(sit["tags"] if tags is None else tags)
    facts = {}
    for fid, g in item["gold_facts"].items():
        t = sorted(set(g["tags"]) & tags)
        if t or not g["tags"]:
            facts[fid] = {"tags": t, "status": g["status"], "likelihood": g.get("likelihood")}
            if quote and t:
                facts[fid]["quote"] = g["text"][:24]
    conds = {c: ("present" if c in tags else "absent") for c in cat.conditions}
    msit = dict(sit, tags=cat.close(tags), uncertain={})
    res = S.compose(cat, item["served"], msit, pi or {})
    who = {I: dict(zip(("gate", "to"), S.gate_result(cat, sit, I, sit["tags"]))) for I in res["actions"]}
    cite = [{"id": c["id"], "issue": c["issue"], "unit": c.get("unit"), "outcome": c["outcome"],
             "reason": sorted(c["reason"]), "X": sorted(c["X"])} for c in item["served"] if c.get("outcome")]
    comp = []
    for c in item["served"]:
        if c.get("outcome"):
            v = S.compare(cat, c, msit["tags"])
            comp.append({"id": c["id"], "issue": c["issue"], "unit": c.get("unit"), "verdict": v["verdict"],
                         "significant": v["significant"]})
    settle = {}
    for I, a in res["actions"].items():
        if (pi or {}).get(I) is not None:
            settle[I] = {"pi": dict(pi[I])}
        elif a["status"] == "settled":
            settle[I] = {"settled": res["assessed"][I]["side"]}
    return {"parses": True, "read": {"facts": facts, "conditions": conds}, "who": who, "cite": cite,
            "compare": comp, "settle": settle, "flags": []}
