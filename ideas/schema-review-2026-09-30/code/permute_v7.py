"""Consistent relabelling for the isomorphic-perturbation test (spec 6): swap side letters per issue, rename
factor IDs, shuffle fact and card order. Works on raw catalog/record documents (dicts), so everything
downstream (solver, validator, reward) sees an ordinary catalog and records."""
import copy, random


def make_perm(cat_doc, seed=0):
    rnd = random.Random(seed)
    c = cat_doc["catalog"]
    swap = {I: rnd.random() < 0.5 for I in c["issues"]}
    ids = list(c["factors"])
    new = [f"Q{rnd.randrange(16**6):06x}" for _ in ids]
    return {"swap": swap, "ren": dict(zip(ids, new)), "rnd": rnd}


def side(P, I, s):
    if s is None or not P["swap"].get(I):
        return s
    return {"A": "B", "B": "A"}.get(s, s)


def tag(P, t):
    stem, _, rung = t.partition("@")
    if stem not in P["ren"]:
        return t                      # conditions and unknown IDs pass through
    return P["ren"][stem] + ("@" + rung if rung else "")


def catalog(P, cat_doc):
    d = copy.deepcopy(cat_doc)
    c = d["catalog"]
    for I, iss in c["issues"].items():
        if P["swap"][I]:
            iss["sides"] = {side(P, I, k): v for k, v in iss["sides"].items()}
            iss["action"] = {side(P, I, k): v for k, v in iss["action"].items()}
            iss["default"] = side(P, I, iss["default"])
    fac = {}
    for fid, f in c["factors"].items():
        f["favors"] = side(P, f["issue"], f["favors"])
        if f.get("mirror_of"):
            f["mirror_of"] = P["ren"][f["mirror_of"]]
        fac[P["ren"][fid]] = f
    c["factors"] = dict(sorted(fac.items()))
    auth = c.get("authority") or {}
    auth["tier_floors"] = {tag(P, k): v for k, v in (auth.get("tier_floors") or {}).items()}
    c["coupling"] = [{"if": {I: side(P, I, s) for I, s in r["if"].items()},
                      "then": {I: side(P, I, s) for I, s in r["then"].items()}} for r in c.get("coupling") or []]
    return d


def atom(P, a):
    a = dict(a)
    if a["act"] in ("proceed", "route"):
        for k in ("side", "recommend", "interim"):
            if isinstance(a.get(k), str):
                a[k] = side(P, a["issue"], a[k])
    elif a["act"] == "contingent":
        a["then"] = dict(a["then"], side=side(P, a["then"]["issue"], a["then"]["side"]))
    return a


def change(P, ch):
    if isinstance(ch, list):
        return [c[0] + tag(P, c[1:]) for c in ch]
    ch = dict(ch)
    for k in ("add", "remove"):
        if ch.get(k):
            ch[k] = [tag(P, t) for t in ch[k]]
    if ch.get("replace_fact"):
        w = dict(ch["replace_fact"]["with"], tags=[tag(P, t) for t in ch["replace_fact"]["with"].get("tags") or []])
        ch["replace_fact"] = dict(ch["replace_fact"], **{"with": w})
    if ch.get("add_order"):
        od = copy.deepcopy(ch["add_order"])
        od["directs"]["side"] = side(P, od["directs"]["issue"], od["directs"]["side"])
        ch["add_order"] = od
    return ch


def record(P, rec_doc):
    d = copy.deepcopy(rec_doc)
    r = d["record"]
    s = r["situation"]
    for f in s["facts"]:
        f["tags"] = [tag(P, t) for t in f["tags"]]
    P["rnd"].shuffle(s["facts"])
    u = s.get("uncertain") or {}
    s["uncertain"] = {tag(P, k): v for k, v in u.items()} if isinstance(u, dict) else \
        [dict(e, tag=tag(P, e["tag"])) for e in u]
    for dl in (s.get("authority") or {}).get("delegations") or []:
        if dl.get("covers_floors"):
            dl["covers_floors"] = [tag(P, t) for t in dl["covers_floors"]]
    for o in s.get("options") or []:
        o["plan"] = [atom(P, a) for a in o["plan"]]
    for od in (s.get("authority") or {}).get("orders") or []:
        od["directs"]["side"] = side(P, od["directs"]["issue"], od["directs"]["side"])
    res = r["resolution"]
    for h in res["holdings"]:
        h["outcome"] = side(P, h["issue"], h["outcome"])
        if h.get("reason"):
            h["reason"] = [tag(P, t) for t in h["reason"]]
        if h.get("reason_alts"):
            h["reason_alts"] = [[tag(P, t) for t in alt] for alt in h["reason_alts"]]
    for x in res.get("routed") or []:
        for k in ("side", "interim", "recommend"):
            if isinstance(x.get(k), str):
                x[k] = side(P, x["issue"], x[k])
    res["plan"] = [atom(P, a) for a in res["plan"]]
    if res.get("hidden_resolution"):
        res["hidden_resolution"] = {I: side(P, I.split("[")[0], v) for I, v in res["hidden_resolution"].items()}
    for fl in (r.get("guidance") or {}).get("flips") or []:
        fl["change"] = change(P, fl["change"])
        for th in (fl["then"] if isinstance(fl["then"], list) else [fl["then"]]):
            for k in ("outcome", "side", "recommend"):
                if isinstance(th.get(k), str):
                    th[k] = side(P, th["issue"], th[k])
        if fl.get("reason"):
            fl["reason"] = [tag(P, t) for t in fl["reason"]]
    return d


def pi(P, dist):
    return {I: {side(P, I, s): p for s, p in d.items()} for I, d in (dist or {}).items()}


def unpermute_action(P, a):
    """Map a composed action back to the original labels for comparison."""
    I = a["issue"]
    out = dict(a)
    for k in ("side", "recommend", "interim"):
        if out.get(k):
            out[k] = side(P, I, out[k])
    return out
