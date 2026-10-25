"""Validator for Benchbook v7 catalogs and records, spec v2 (drafts/SPEC-v7-v2.md sections 1-3).

    python3 validate_v7.py [files...]      (default: catalogs/*.yaml records/*.yaml; exit 1 on any error)

Layers: (1) JSON Schema (v7.schema.json, draft 2020-12); (2) catalog lints of spec 1 on the merged view
([v2] `imports` resolved from the catalog's directory; collisions are errors); (3) record lints of spec 2
([v2] channel, determination `by`, data-channel conditions, established_by, units, reason_alts) and the gold
round trip: solver_v3 composes the plan from the record's own cards (and, CHOICE, pi = the one-hot
hidden_resolution for unsettled issues) and compares it atom by atom with `resolution.plan`."""
import glob, json, os, sys
import jsonschema
import solver_v3 as S

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = json.load(open(os.path.join(HERE, "v7.schema.json")))
NONSPEC = {"order": {"text", "equity", "issued"}, "routed": {"recommend"}, "authority": {"flag_to"},
           "flip": {"actor", "form", "source_unsure", "scope"},
           "then": {"recommend", "residue", "urgency", "act"},
           "proceed": {"to", "question", "ask", "what", "urgency"}, "route": {"ask", "what"},
           "residue": {"to"}, "duty": {"to"}, "contingent": set()}


def schema_errors(doc):
    v = jsonschema.Draft202012Validator(SCHEMA)
    return [f"schema: {'/'.join(map(str, e.absolute_path))}: {e.message[:160]}" for e in v.iter_errors(doc)]


def merged_catalog(doc, path=None, flags=None):
    c = doc.get("catalog", doc)
    fl = {f.get("flag") for f in (c.get("factors") or {}).values() if f.get("flag")} if flags is None else flags
    return S.Catalog(doc, fl, [os.path.dirname(os.path.abspath(path))] if path else [HERE + "/catalogs"])


def lint_catalog(doc, path=None):
    """Spec 1 rules on the merged view. Returns (errors, warnings)."""
    E, W = [], []
    try:
        cat = merged_catalog(doc, path)
    except (KeyError, ValueError) as e:
        return [f"imports: {e}"], W
    for k, key in cat.collisions:
        E.append(f"imports: {k} id {key} collides with an imported entry")
    issues, eqs, acts, auth = cat.issues, cat.equity_defs, cat.actions, cat.auth
    for I, iss in issues.items():
        if set(iss["sides"]) != set(iss["action"]):
            E.append(f"issue {I}: sides and action letters differ")
        if iss["default"] not in iss["sides"]:
            E.append(f"issue {I}: default {iss['default']} is not a side")
        for cls in iss["action"].values():
            if cls not in acts:
                E.append(f"issue {I}: action class {cls} not defined")
    for fid, f in cat.all_factors.items():
        if fid.startswith("cond."):
            E.append(f"factor {fid}: factor IDs may not use the condition prefix")
        if f["issue"] not in issues:
            E.append(f"factor {fid}: unknown issue {f['issue']}")
            continue
        if f["favors"] not in issues[f["issue"]]["sides"]:
            E.append(f"factor {fid}: favors {f['favors']} is not a side of {f['issue']}")
        names = f["equities"]
        if isinstance(names, list) and "rungs" not in f:
            E.append(f"factor {fid}: the list form of `equities` needs rungs (the rung strength governs)")
        maps = [("equities", names)] if isinstance(names, dict) else []
        for e in (names if isinstance(names, list) else names.keys()):
            if e not in eqs:
                E.append(f"factor {fid}: unknown equity {e}")
        if "rungs" in f:
            order = cat.dimensions.get(f.get("dimension"))
            if order is None:
                E.append(f"factor {fid}: unknown dimension {f.get('dimension')}")
            elif any(k not in order for k in f["rungs"]) or list(f["rungs"]) != sorted(f["rungs"], key=order.index):
                E.append(f"factor {fid}: rungs not in the dimension's order")
            maps += [(f"rung {r}", v) for r, v in f["rungs"].items() if isinstance(v, dict)]
            if isinstance(names, dict) and any(isinstance(v, str) for v in f["rungs"].values()):
                W.append(f"factor {fid}: map-form equities with string rungs; [v2] use the list form (rung strength governs)")
        for where, m in maps:
            vals = [S.STRENGTH[v] for v in m.values()]
            if len(vals) > 1 and max(vals[1:]) > vals[0] and not f.get("conjunctive"):
                E.append(f"factor {fid} ({where}): a secondary equity is stronger than the first (M2 lint); "
                         f"reorder or mark conjunctive: true")
        if f.get("mirror_of"):
            g = cat.all_factors.get(f["mirror_of"])
            if not g or g["issue"] != f["issue"] or g["favors"] == f["favors"] or g.get("dimension") != f.get("dimension"):
                E.append(f"factor {fid}: mirror_of must name an opposite-side factor on the same issue and dimension")
    for p in cat.prohibitions:
        if p["forbids"]["action"] not in acts:
            E.append(f"prohibition {p.get('id')}: unknown action {p['forbids']['action']}")
        for c in (p.get("when") or []) + (p.get("unless") or []):
            if not cat.known(c) and c not in cat.all_factors:
                E.append(f"prohibition {p.get('id')}: unknown condition {c}")
    for cls, a in acts.items():
        if a.get("tier") and cat.tiers and a["tier"] not in cat.tiers:
            E.append(f"action {cls}: unknown tier {a['tier']}")
        if a.get("direction") == "restrictive" and cls in (auth.get("non_delegable_to_agent") or []):
            E.append(f"action {cls}: restrictive classes need no level (non_delegable)")
    for t, lvl in cat.tiers.items():
        if lvl not in cat.levels:
            E.append(f"tier {t}: level {lvl} not in levels")
        if t not in cat.stakes:
            E.append(f"tier {t}: no stakes (L, k)")
    for role, lvl in (auth.get("roles") or {}).items():
        if lvl is not None and lvl not in cat.levels:
            E.append(f"role {role}: level {lvl} not in levels")
    if set(auth.get("inherent") or []) & set(auth.get("non_delegable_to_agent") or []):
        E.append("a class is both inherent and non_delegable_to_agent")
    for t in (auth.get("tier_floors") or {}):
        if t not in cat.tag:
            E.append(f"tier_floors: {t} is not a factor tag")
    for rule in cat.coupling:
        for part in (rule["if"], rule["then"]):
            for I, s in part.items():
                if I not in issues or s not in issues[I]["sides"]:
                    E.append(f"coupling: {I}:{s} is not an issue side")
    return E, W


def hidden_pi(cat, r):
    """CHOICE: the author's hidden_resolution as a one-hot pi per unsettled issue (keys 'I' or 'I[unit]')."""
    h = (r.get("resolution") or {}).get("hidden_resolution") or {}
    return {k: {s: float(s == v) for s in cat.sides(k.split("[")[0])} for k, v in h.items() if k.split("[")[0] in cat.issues}


def _nonspec(W, where, d, kind):
    extra = sorted(set(d) & NONSPEC[kind])
    if extra:
        W.append(f"{where}: keys outside the spec (ignored): {extra}")


def lint_record(cat, doc, round_trip=True):
    """Record rules of spec 2 (v2) and the gold round trip. Returns (errors, warnings)."""
    r = doc.get("record", doc)
    E, W = [], []
    full = S.Catalog({"catalog": cat.raw}, flags={f.get("flag") for f in cat.all_factors.values() if f.get("flag")})
    if r["catalog"] != f"{cat.id}@{cat.version}":
        W.append(f"catalog reference {r['catalog']} != {cat.id}@{cat.version}")
    units = {u["id"] for u in r.get("units") or []}
    kind = (r.get("provenance") or {}).get("kind")
    auth = r["situation"].get("authority") or {}
    holders = {d["holder"] for d in auth.get("deciders") or []}
    ids, found, sit_tags = set(), [], set()
    for f in r["situation"]["facts"]:
        if f["id"] in ids:
            E.append(f"fact {f['id']}: duplicate id")
        ids.add(f["id"])
        bad = [t for t in f["tags"] if not full.known(t)]
        if bad:
            E.append(f"fact {f['id']}: tags not in catalog {bad}")
        off = [t for t in f["tags"] if full.known(t) and not cat.known(t)]
        if off:
            W.append(f"fact {f['id']}: tags behind a catalog flag (dropped unless the flag is on): {off}")
        good = [t for t in f["tags"] if full.known(t)]
        if set(full.close(good)) != set(good):
            W.append(f"fact {f['id']}: tags not closed downward {f['tags']} (3.0 closes them)")
        if f["status"] == "found" and f.get("known_at_decision", True):
            found.append(f["id"])
        if f["status"] == "determination" and f.get("by") not in holders:
            E.append(f"fact {f['id']}: a determination's `by` must name a holder in situation.authority ([v2] H5)")
        conds = [t for t in f["tags"] if full.is_cond(t)]
        if f.get("channel") == "data" and conds:
            E.append(f"fact {f['id']}: data-channel fact carries condition tags {conds} (P7)")
        for c in conds:
            ok, why = S.condition_ok(full, f, c)
            if not ok and f.get("channel") != "data":
                W.append(f"fact {f['id']}: {c} will be dropped in 3.0: {why}")
        for u in S.as_list(f.get("about")):
            if u not in units:
                E.append(f"fact {f['id']}: about {u} is not a declared unit")
        sit_tags |= set(full.close(good))
    if found:
        (W if kind in ("adjudicated", "investigated") else E).append(
            f"facts {found}: status `found` in the situation layer (leaks the decision; P1)")
    _nonspec(W, "authority", auth, "authority")
    for od in auth.get("orders") or []:
        _nonspec(W, f"order {od.get('id')}", od, "order")
        if od["directs"]["issue"] not in cat.issues:
            E.append(f"order {od.get('id')}: unknown issue")
        elif od.get("from") not in holders:
            W.append(f"order {od.get('id')}: from {od.get('from')!r} is not a decider, so it authorizes nothing (H2a)")
    unc = S.situation_from_record(full, r)["uncertain"]            # explicit + disputed facts
    res = r["resolution"]
    for h in res["holdings"]:
        I = h["issue"]
        if I not in cat.issues:
            E.append(f"holding {I}: unknown issue")
            continue
        if h["outcome"] not in cat.sides(I):
            E.append(f"holding {I}: outcome {h['outcome']} is not a side")
        hu = S.as_list(h.get("units"))
        for u in hu:
            if u not in units:
                E.append(f"holding {I}: unit {u} not declared")
        ut = S._units_tags(full, r, hu)
        for alt in h.get("reason_alts") or [h.get("reason") or []]:
            conds = [t for t in alt if full.is_cond(t)]
            if conds:
                E.append(f"holding {I}: conditions never appear in a reason {conds}")
            miss = {t for t in set(full.close([x for x in alt if x not in conds])) - ut if full.stem(t) not in unc}
            if miss:
                E.append(f"holding {I}: reason not present at or above its rung {sorted(miss)}")
            wrong = [t for t in alt if t in full.tag and (full.issue_of(t) != I or full.side(t) != h["outcome"])]
            if wrong:
                W.append(f"holding {I}: reason factors off the issue or favoring the other side {wrong}")
    for x in res.get("routed") or []:
        _nonspec(W, f"routed {x['issue']}", x, "routed")
    for fl in (r.get("guidance") or {}).get("flips") or []:
        _nonspec(W, f"flip {fl['id']}", fl, "flip")
        ch = S._change(fl)
        bad = [t for t in (ch.get("add") or []) + (ch.get("remove") or []) if not full.known(t)]
        if bad:
            E.append(f"flip {fl['id']}: change names unknown tags {bad}")
        for th in S.as_list(fl["then"]):
            _nonspec(W, f"flip {fl['id']} then", th, "then")
            if th["issue"] not in cat.issues:
                E.append(f"flip {fl['id']}: unknown issue {th['issue']}")
        if ch.get("add") and not ch.get("about") and set(full.close(ch["add"])) <= sit_tags and not ch.get("replace_fact"):
            W.append(f"flip {fl['id']}: change adds only tags already present (a no-op)")
    for atom in res["plan"] + [a for o in r["situation"].get("options") or [] for a in o["plan"]]:
        I = atom.get("issue") or (atom.get("then") or {}).get("issue")
        if atom["act"] in ("proceed", "route", "contingent") and I not in cat.issues:
            E.append(f"plan atom {atom}: unknown issue")
        for u in S.as_list(atom.get("units")):
            if u not in units:
                E.append(f"plan atom: unit {u} not declared")
    for atom in res["plan"]:
        if atom["act"] in NONSPEC:
            _nonspec(W, f"plan atom {atom['act']} {atom.get('issue', atom.get('equity', ''))}", atom, atom["act"])
    if E or not round_trip:
        return E, W
    cards = S.cards_from_record(cat, r)
    got = S.compose_record(cat, r, cards, hidden_pi(cat, r))
    d = S.plan_diff(res["plan"], got["plan"])
    for k in d["missing"]:
        E.append(f"round trip: gold atom not produced {k}")
    for k in d["extra"]:
        E.append(f"round trip: solver atom not in gold {k}")
    for k, bad in d["attr"]:
        E.append(f"round trip: {k} differs {bad}")
    for bad in S.lint_horty(cat, cards):
        W.append(f"Horty/naqd lint: {bad['p'][0]} and {bad['q'][0]} both force opposite outcomes on {bad['Y']}")
    return E, W


def load_all(paths):
    cats, recs = {}, {}
    for p in paths:
        d = S.load_yaml(p)
        (cats if "catalog" in d else recs)[p] = d
    return cats, recs


def catalog_for(rec_path, rec_doc, cats):
    """The catalog with the record's id@version, preferring one whose directory name matches the record's."""
    cid = rec_doc["record"]["catalog"].split("@")[0]
    cand = [p for p, d in cats.items() if d["catalog"]["id"] == cid]
    same = [p for p in cand if os.path.basename(os.path.dirname(p)) == os.path.basename(os.path.dirname(rec_path))]
    return (same or cand or [None])[0]


def main(paths, quiet=False):
    cats, recs = load_all(paths)
    nerr, out = 0, []
    loaded = {}
    for p, d in cats.items():
        E = schema_errors(d)
        W = []
        if not E:
            E, W = lint_catalog(d, p)
        if not E and d["catalog"].get("issues"):
            loaded[p] = merged_catalog(d, p)
        holders = {x["holder"] for q, r in recs.items() if catalog_for(q, r, cats) == p
                   for x in (r["record"]["situation"].get("authority") or {}).get("deciders") or []}
        if p in loaded:
            for c, v in loaded[p].conditions.items():
                if v.get("unreachable") and v["unreachable"] not in holders:
                    W.append(f"{c}: unreachable {v['unreachable']!r} names no decider in any record ([v2] lint)")
        nerr += len(E)
        out.append((p, E, W))
    for p, d in recs.items():
        E, W = schema_errors(d), []
        cp = catalog_for(p, d, cats)
        if cp not in loaded:
            E.append(f"no valid catalog for {d['record']['catalog']}")
        elif not E:
            E, W = lint_record(loaded[cp], d)
        nerr += len(E)
        out.append((p, E, W))
    if not quiet:
        for p, E, W in out:
            print(f"{'FAIL' if E else 'ok  '} {os.path.relpath(p, HERE)}")
            for m in E: print("   E", m)
            for m in W: print("   W", m)
    return nerr if not quiet else (nerr, out)


if __name__ == "__main__":
    args = sys.argv[1:] or sorted(glob.glob(os.path.join(HERE, "catalogs/*.yaml"))) + \
        sorted(glob.glob(os.path.join(HERE, "records/*.yaml")))
    sys.exit(1 if main(args) else 0)
