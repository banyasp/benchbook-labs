#!/usr/bin/env python3
"""Resolution check for the hard-calls v2 conversion (round 2).

    python3 check_v2.py            # run from anywhere; checks the directory this file is in

1. Every *.yaml parses with yaml.safe_load.
2. Every catalog resolves: imports load, ids do not collide across imports, every internal reference
   (issue -> action, factor -> issue/equity/dimension, prohibition -> action/condition, tier_floors -> factor, ...) exists.
3. Every record resolves against its catalog (with imports): every tag on a fact, every reason id, every condition,
   every issue / side / action / equity / unit id used anywhere in the record (situation, resolution, guidance).
4. Spec-v2 record lints: channel on every fact, `by` on every determination and on holders in established_by,
   a reason factor's issue and side match the holding, `units` refer to declared units.
Exit code 1 on any ERROR; WARNs are reported but do not fail.
"""
import glob
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ERR, WARN, INFO = [], [], []


def err(where, msg):
    ERR.append(f"ERROR  {where}: {msg}")


def warn(where, msg):
    WARN.append(f"WARN   {where}: {msg}")


def load(path):
    try:
        with open(path) as fh:
            return yaml.safe_load(fh)
    except Exception as e:  # noqa
        err(os.path.basename(path), f"does not parse: {e}")
        return None


# ---------------------------------------------------------------- catalogs
def catalog_files():
    out = {}
    for p in sorted(glob.glob(os.path.join(HERE, "catalog-*.yaml"))):
        d = load(p)
        if d and "catalog" in d:
            c = d["catalog"]
            out[c["id"]] = (os.path.basename(p), c)
    return out


SECTIONS = ["issues", "equities", "dimensions", "factors", "conditions", "actions"]


def merged(cat_id, cats, seen=None):
    """Return a merged view of a catalog and its imports (imports first)."""
    seen = seen or []
    fname, c = cats[cat_id]
    view = {k: {} for k in SECTIONS}
    view["prohibitions"] = []
    for imp in c.get("imports") or []:
        iid, _, ver = imp.partition("@")
        if iid not in cats:
            err(fname, f"import {imp}: no catalog {iid}")
            continue
        if ver != str(cats[iid][1].get("version")):
            err(fname, f"import {imp}: version is {cats[iid][1].get('version')}")
        if iid in seen:
            err(fname, f"import cycle at {iid}")
            continue
        sub = merged(iid, cats, seen + [cat_id])
        for k in SECTIONS:
            for key, val in sub[k].items():
                if key in view[k]:
                    err(fname, f"{k} id {key} collides between imports")
                view[k][key] = val
        view["prohibitions"] += sub["prohibitions"]
    for k in SECTIONS:
        for key, val in (c.get(k) or {}).items():
            if key in view[k]:
                err(fname, f"{k} id {key} duplicates an imported entry (remove the duplicate)")
            view[k][key] = val
    view["prohibitions"] += c.get("prohibitions") or []
    view["authority"] = c.get("authority") or {}
    view["coupling"] = c.get("coupling") or []
    view["stakes"] = c.get("stakes")
    return view


def split_tag(tag):
    base, _, rung = str(tag).partition("@")
    return base, rung


def rungs_of(view, dim):
    d = view["dimensions"].get(dim)
    if d is None:
        return None
    return d["rungs"] if isinstance(d, dict) else d


def tag_ok(view, tag, where, allow_cond=True, allow_factor=True):
    base, rung = split_tag(tag)
    if base.startswith("cond."):
        if not allow_cond:
            err(where, f"condition {tag} not allowed here")
        elif base not in view["conditions"]:
            err(where, f"unknown condition {base}")
        return
    if base not in view["factors"]:
        err(where, f"unknown tag/factor {base}")
        return
    if not allow_factor:
        err(where, f"factor {tag} not allowed here")
    f = view["factors"][base]
    if rung:
        rs = rungs_of(view, f.get("dimension")) if f.get("dimension") else None
        if rs is None or rung not in rs:
            err(where, f"tag {tag}: rung {rung} not on dimension {f.get('dimension')}")
    elif f.get("dimension"):
        pass  # a bare scaled tag is allowed (any rung) but unusual
    return


def check_catalog(cid, cats):
    fname, c = cats[cid]
    v = merged(cid, cats)
    loc = fname
    for I, iss in v["issues"].items():
        if set(iss["sides"]) != set(iss["action"]):
            err(loc, f"issue {I}: sides and action letters differ")
        if iss["default"] not in iss["sides"]:
            err(loc, f"issue {I}: default {iss['default']} is not a side")
        for s, a in iss["action"].items():
            if a not in v["actions"]:
                err(loc, f"issue {I}: action {a} (side {s}) not defined")
    for fid, f in v["factors"].items():
        if fid.startswith("cond."):
            err(loc, f"factor {fid}: uses the condition prefix")
        if f.get("issue") not in v["issues"]:
            err(loc, f"factor {fid}: unknown issue {f.get('issue')}")
            continue
        if f.get("favors") not in v["issues"][f["issue"]]["sides"]:
            err(loc, f"factor {fid}: favors {f.get('favors')} is not a side of {f['issue']}")
        eqs = f.get("equities")
        names = list(eqs) if isinstance(eqs, (dict, list)) else []
        if not names:
            err(loc, f"factor {fid}: no equities")
        for e in names:
            if e not in v["equities"]:
                err(loc, f"factor {fid}: unknown equity {e}")
        if f.get("dimension"):
            rs = rungs_of(v, f["dimension"])
            if rs is None:
                err(loc, f"factor {fid}: unknown dimension {f['dimension']}")
            else:
                ks = list(f.get("rungs") or {})
                if not ks:
                    err(loc, f"factor {fid}: scaled factor with no rungs")
                for k in ks:
                    if k not in rs:
                        err(loc, f"factor {fid}: rung {k} not in dimension {f['dimension']}")
                if ks and ks != sorted(ks, key=lambda r: rs.index(r) if r in rs else 99):
                    err(loc, f"factor {fid}: rungs not in dimension order")
                if isinstance(eqs, dict):
                    warn(loc, f"factor {fid}: scaled factor with map-form equities (v2 uses list form)")
        elif f.get("rungs"):
            err(loc, f"factor {fid}: rungs without dimension")
    for cn, cond in v["conditions"].items():
        if not cn.startswith("cond."):
            err(loc, f"condition {cn}: missing cond. prefix")
        for eb in cond.get("established_by") or []:
            if "holder" not in eb or "form" not in eb:
                err(loc, f"condition {cn}: established_by entry needs holder and form")
    for a, act in v["actions"].items():
        if act.get("direction") not in ("permissive", "restrictive"):
            err(loc, f"action {a}: direction")
        if act.get("direction") == "permissive" and "tier" not in act:
            err(loc, f"action {a}: permissive action without tier")
    for p in v["prohibitions"]:
        w = f"{loc} prohibition {p.get('id')}"
        act = (p.get("forbids") or {}).get("action")
        if act not in v["actions"]:
            err(w, f"forbids unknown action {act}")
        for k in ("when", "unless"):
            for t in p.get(k) or []:
                if t not in v["conditions"]:
                    err(w, f"{k}: unknown condition {t}")
        if not p.get("when"):
            err(w, "empty when")
    au = v["authority"]
    tiers = au.get("tiers") or {}
    levels = au.get("levels") or []
    if c.get("id") != "CORE":
        for k in ("levels", "tiers", "roles"):
            if k not in au:
                err(loc, f"authority.{k} missing")
        for t, lv in tiers.items():
            if lv not in levels:
                err(loc, f"tier {t}: level {lv} unknown")
    for a, act in v["actions"].items():
        if act.get("tier") and c.get("id") != "CORE" and act["tier"] not in tiers:
            err(loc, f"action {a}: unknown tier {act['tier']}")
    for key, t in (au.get("tier_floors") or {}).items():
        base, rung = split_tag(key)
        if base not in v["factors"]:
            err(loc, f"tier_floors: unknown factor {base}")
        elif rung:
            tag_ok(v, key, f"{loc} tier_floors")
        if t not in tiers:
            err(loc, f"tier_floors {key}: unknown tier {t}")
    for a in (au.get("non_delegable_to_agent") or []) + (au.get("inherent") or []):
        if a not in v["actions"]:
            err(loc, f"authority list names unknown action {a}")
    for cp in v["coupling"]:
        for part in (cp.get("if") or {}, cp.get("then") or {}):
            for I, s in part.items():
                if I not in v["issues"] or s not in v["issues"][I]["sides"]:
                    err(loc, f"coupling {I}:{s} unknown")
    for e, eq in v["equities"].items():
        for a in eq.get("residue") or []:
            if a not in v["actions"]:
                err(loc, f"equity {e}: residue action {a} unknown")
    return v


# ---------------------------------------------------------------- records
def as_list(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def check_record(path, cats, views):
    fname = os.path.basename(path)
    d = load(path)
    if not d:
        return None
    r = d["record"]
    cat_ref = r["catalog"]
    cid, _, ver = cat_ref.partition("@")
    if cid not in views:
        err(fname, f"catalog {cat_ref} not found")
        return None
    if ver != str(cats[cid][1].get("version")):
        err(fname, f"catalog version {ver} != {cats[cid][1].get('version')}")
    v = views[cid]
    units = {u["id"] for u in r.get("units") or []}
    sit, res, gd = r["situation"], r["resolution"], r["guidance"]
    auth = sit.get("authority") or {}
    holders = {x["holder"] for x in auth.get("deciders") or []}
    delegatees = {x["to"] for x in auth.get("delegations") or []}
    flag_targets = set(auth.get("flag_to") or [])
    known_people = holders | delegatees | flag_targets

    def unit_ok(u, where):
        for x in as_list(u):
            if x not in units:
                err(where, f"unit {x} not declared in record.units")

    def issue_ok(I, s, where):
        if I not in v["issues"]:
            err(where, f"unknown issue {I}")
            return False
        if s is not None and s not in v["issues"][I]["sides"]:
            err(where, f"issue {I} has no side {s}")
            return False
        return True

    def cond_list(lst, where):
        for t in as_list(lst):
            if not str(t).startswith("cond.") or t not in v["conditions"]:
                err(where, f"unknown condition {t}")

    def people(lst, where, strict=False):
        for p in as_list(lst):
            if p not in known_people:
                (err if strict else warn)(where, f"addressee '{p}' is not a decider, delegatee or flag_to entry")

    # facts
    ids = set()
    for f in sit["facts"]:
        w = f"{fname} fact {f.get('id')}"
        if f["id"] in ids:
            err(w, "duplicate fact id")
        ids.add(f["id"])
        if f.get("channel") not in ("principal", "data", "sensor", "record"):
            err(w, f"channel missing or invalid: {f.get('channel')}")
        if f.get("status") == "determination" and not f.get("by"):
            err(w, "determination without by")
        if f.get("by") and f["by"] not in holders:
            err(w, f"by: {f['by']} is not a decider")
        if f.get("status") == "assessed" and not (f.get("likelihood") and f.get("confidence")):
            err(w, "assessed needs likelihood and confidence")
        if "about" in f:
            unit_ok(f["about"], w)
        for t in f.get("tags") or []:
            tag_ok(v, t, w)
            if f.get("channel") == "data" and str(t).startswith("cond."):
                cd = v["conditions"].get(split_tag(t)[0], {})
                if cd.get("established_by") or cd.get("kind") == "frame":
                    err(w, f"data-channel fact carries authority-gating condition {t} (P7)")
    for u in sit.get("uncertain") or []:
        tag_ok(v, u["tag"], f"{fname} uncertain")
    # authority
    for dcd in auth.get("deciders") or []:
        for a in dcd.get("holds") or []:
            if a not in v["actions"]:
                err(f"{fname} decider {dcd['holder']}", f"unknown action {a}")
    for dl in auth.get("delegations") or []:
        w = f"{fname} delegation {dl['id']}"
        for a in dl.get("holds") or []:
            if a not in v["actions"]:
                err(w, f"unknown action {a}")
        for a in dl.get("duties") or []:
            if a not in v["actions"]:
                err(w, f"duty action {a} unknown")
        cond_list(dl.get("when"), w)
        for t in dl.get("covers_floors") or []:
            tag_ok(v, t, w)
    for o in auth.get("orders") or []:
        w = f"{fname} order {o['id']}"
        if o["from"] not in holders:
            warn(w, f"from '{o['from']}' is not a decider: it authorizes nothing (H2a)")
        dr = o["directs"]
        issue_ok(dr["issue"], dr["side"], w)
        unit_ok(dr.get("units"), w)
        for k in ("active_when", "disabled_by", "superseded_by", "excludes_when"):
            cond_list(o.get(k), f"{w} {k}")
        for e in o.get("excludes") or []:
            if e not in v["equities"]:
                err(w, f"excludes unknown equity {e}")
        if o.get("equity") and o["equity"] not in v["equities"]:
            err(w, f"unknown equity {o['equity']}")
    for q in auth.get("requests") or []:
        if q.get("fact") and q["fact"] not in ids:
            err(f"{fname} request", f"unknown fact {q['fact']}")
    # options
    def atom_ok(a, where):
        act = a.get("act")
        if "issue" in a:
            issue_ok(a["issue"], a.get("side"), where)
        unit_ok(a.get("units"), where)
        if act in ("residue",):
            if a["equity"] not in v["equities"]:
                err(where, f"unknown equity {a['equity']}")
            for x in a.get("atoms") or []:
                if x not in v["actions"]:
                    err(where, f"unknown action {x}")
        if act == "duty":
            for x in a.get("atoms") or []:
                if x not in v["actions"]:
                    err(where, f"unknown action {x}")
            if a.get("from") not in {d["id"] for d in auth.get("delegations") or []}:
                err(where, f"duty from unknown delegation {a.get('from')}")
        if act == "contingent":
            cond_list(a.get("when"), where)
            t = a["then"]
            issue_ok(t["issue"], t.get("side"), where)
        if act == "route":
            people(a.get("to"), where)
            if a.get("because") and a["because"] not in ("authorize", "inform", "flag"):
                err(where, f"route type {a['because']}")
        if act == "proceed" and a.get("to"):
            people(a.get("to"), where)
        if act not in ("proceed", "route", "residue", "duty", "contingent"):
            err(where, f"unknown atom kind {act}")
    for i, op in enumerate(sit.get("options") or []):
        for a in op["plan"]:
            atom_ok(a, f"{fname} option {i}")
    # resolution
    for h in res["holdings"]:
        w = f"{fname} holding {h['issue']}:{h['outcome']}"
        if not issue_ok(h["issue"], h["outcome"], w):
            continue
        unit_ok(h.get("units"), w)
        alts = h.get("reason_alts") or ([h["reason"]] if h.get("reason") else [])
        if h.get("reason") and h.get("reason_alts"):
            warn(w, "both reason and reason_alts")
        if not alts:
            err(w, "no reason")
        for alt in alts:
            for t in alt:
                tag_ok(v, t, w, allow_cond=False)
                base, rung = split_tag(t)
                fac = v["factors"].get(base)
                if fac:
                    if fac["issue"] != h["issue"]:
                        err(w, f"reason {t} belongs to issue {fac['issue']}")
                    if fac["favors"] != h["outcome"]:
                        err(w, f"reason {t} favors {fac['favors']}, holding outcome is {h['outcome']}")
        # reason rungs must be carried by some fact tag
        carried = {t for f in sit["facts"] for t in f.get("tags") or []}
        for alt in alts:
            for t in alt:
                if t not in carried:
                    warn(w, f"reason tag {t} is not carried by any situation fact")
        if h.get("force") not in ("required", "permitted"):
            err(w, f"force {h.get('force')}")
    for rt in res.get("routed") or []:
        w = f"{fname} routed {rt['issue']}"
        issue_ok(rt["issue"], rt.get("side"), w)
        if rt.get("interim"):
            issue_ok(rt["issue"], rt["interim"], w)
        unit_ok(rt.get("units"), w)
        people(rt.get("to"), w)
        if rt.get("because") not in ("authorize", "inform", "flag"):
            err(w, f"route type {rt.get('because')}")
    for a in res["plan"]:
        atom_ok(a, f"{fname} plan")
    if res.get("status") not in ("settled", "contested"):
        err(fname, f"status {res.get('status')}")
    hr = res.get("hidden_resolution") or {}
    if not isinstance(hr, dict):
        err(fname, "hidden_resolution must be a dict issue -> side")
        hr = {}
    for key, side in hr.items():
        base, _, unit = key.partition("[")
        issue_ok(base, side, f"{fname} hidden_resolution")
        if unit:
            unit_ok(unit.rstrip("]"), f"{fname} hidden_resolution")
    for h in res["holdings"]:
        if h.get("force") == "permitted" and h["issue"] not in {k.partition("[")[0] for k in hr}:
            warn(fname, f"holding {h['issue']}:{h['outcome']} is permitted (unsettled) but has no hidden_resolution entry")
    # guidance
    def then_ok(t, w):
        for c in as_list(t):
            issue_ok(c["issue"], c.get("outcome") or c.get("side"), w)
            unit_ok(c.get("units"), w)
            if c.get("route") and c["route"] not in ("authorize", "inform", "flag"):
                err(w, f"route type {c['route']}")
            people(c.get("to"), w)
            for x in c.get("residue") or []:
                if x not in v["actions"]:
                    err(w, f"residue action {x}")
    for fl in gd["flips"]:
        w = f"{fname} flip {fl['id']}"
        if fl.get("event") not in ("world", "decision", "refusal", "request_change", "lapse"):
            err(w, f"event {fl.get('event')}")
        ch = fl["change"]
        if not isinstance(ch, dict):
            err(w, "change must be a dict (v2 grammar)")
            ch = {}
        unit_ok(ch.get("about"), w)
        for t in (ch.get("add") or []) + (ch.get("remove") or []):
            tag_ok(v, t, w)
        rf = ch.get("replace_fact")
        if rf:
            if rf["id"] not in ids:
                err(w, f"replace_fact: unknown fact {rf['id']}")
            for t in rf["with"].get("tags") or []:
                tag_ok(v, t, w)
            if rf["with"].get("channel") not in ("principal", "data", "sensor", "record"):
                err(w, "replace_fact.with: bad channel")
        ao = ch.get("add_order")
        if ao:
            dr = ao["directs"]
            issue_ok(dr["issue"], dr["side"], w)
            unit_ok(dr.get("units"), w)
            for k in ("active_when", "disabled_by", "superseded_by", "excludes_when"):
                cond_list(ao.get(k), f"{w} add_order.{k}")
            for e in ao.get("excludes") or []:
                if e not in v["equities"]:
                    err(w, f"excludes unknown equity {e}")
            if ao["from"] not in holders:
                warn(w, f"add_order.from '{ao['from']}' is not a decider")
        for t in fl.get("reason") or []:
            tag_ok(v, t, w, allow_cond=False)
        then_ok(fl["then"], w)
        if fl.get("actor") and fl["actor"] not in known_people and fl["actor"] not in ("analyst",):
            warn(w, f"actor '{fl['actor']}' is not a decider, delegatee or flag_to entry")
    for fo in gd.get("foils") or []:
        for t in fo.get("defeated_by") or []:
            base = split_tag(t)[0]
            if base in v["factors"] or base in v["conditions"]:
                continue
            if base in {d["id"] for d in auth.get("delegations") or []}:
                continue
            if base in (v["authority"].get("non_delegable_to_agent") or []) or base == "non_delegable_to_agent":
                continue
            if base.startswith("channel:"):
                continue
            err(f"{fname} foil", f"defeated_by {t} does not resolve")
    # INFO: gate conditions (order.active_when, delegation.when) that no fact tags. Some are deliberately absent
    # (e.g. REL d1 waits for an originator approval that has not happened); the rest are dead gates.
    carried = {t for f in sit["facts"] for t in f.get("tags") or []}
    for o in auth.get("orders") or []:
        for c in o.get("active_when") or []:
            if c not in carried:
                INFO.append(f"INFO   {fname} order {o['id']}: active_when {c} is not tagged on any fact (order is NOT live as written)")
    for dl in auth.get("delegations") or []:
        for c in dl.get("when") or []:
            if c not in carried:
                INFO.append(f"INFO   {fname} delegation {dl['id']}: when {c} is not tagged on any fact (delegation inactive as written)")
    return r


def main():
    files = sorted(glob.glob(os.path.join(HERE, "*.yaml")))
    print(f"{len(files)} yaml files")
    cats = catalog_files()
    views = {}
    for cid in cats:
        views[cid] = check_catalog(cid, cats)
    recs = []
    for p in files:
        if os.path.basename(p).startswith("catalog-"):
            continue
        recs.append(check_record(p, cats, views))
    # cross-record lints
    all_holders = set()
    for r in recs:
        if r:
            for dcd in r["situation"]["authority"].get("deciders") or []:
                all_holders.add(dcd["holder"])
    for cid, (fname, c) in cats.items():
        for cn, cond in (views[cid]["conditions"] or {}).items():
            if cond.get("unreachable") and cond["unreachable"] not in all_holders:
                warn(fname, f"{cn}.unreachable '{cond['unreachable']}' is not a decider in any record (v2 lint)")
            for eb in cond.get("established_by") or []:
                if eb["holder"] not in all_holders:
                    warn(fname, f"{cn}.established_by holder '{eb['holder']}' is not a decider in any record")
    for line in INFO:
        print(line)
    for line in WARN:
        print(line)
    for line in ERR:
        print(line)
    print(f"\n{len([r for r in recs if r])} records, {len(cats)} catalogs; {len(ERR)} errors, {len(WARN)} warnings")
    return 1 if ERR else 0


if __name__ == "__main__":
    sys.exit(main())
