"""Validator for Benchbook v7 catalogs and records (spec 1-2; lints from 1 and 3.6).

    python3 validate_v7.py catalogs/*.yaml records/*.yaml      (exit 1 on any error)

Three layers: (1) JSON Schema (v7.schema.json, draft 2020-12); (2) the catalog lints of spec 1;
(3) record lints: tags known and closed, statuses, reason rungs <= observed, the gold plan reproduced by
solver_v3 from the record's own holdings + gate, and the Horty (naqd) lint over its compiled cards."""
import glob, json, os, sys
import jsonschema
import solver_v3 as S

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = json.load(open(os.path.join(HERE, "v7.schema.json")))
LIKELIHOOD = ["almost_no_chance", "very_unlikely", "unlikely", "even", "likely", "very_likely", "almost_certain"]


def schema_errors(doc):
    v = jsonschema.Draft202012Validator(SCHEMA)
    return [f"schema: {'/'.join(map(str, e.absolute_path))}: {e.message[:160]}" for e in v.iter_errors(doc)]


def lint_catalog(doc):
    """Spec 1 rules plus referential checks. Returns (errors, warnings)."""
    c = doc.get("catalog", doc)
    E, W = [], []
    issues, eqs = c.get("issues") or {}, c.get("equities") or {}
    dims = {d: (v["rungs"] if isinstance(v, dict) else v) for d, v in (c.get("dimensions") or {}).items()}
    acts, auth = c.get("actions") or {}, c.get("authority") or {}
    levels, tiers = auth.get("levels") or [], auth.get("tiers") or {}
    for I, iss in issues.items():
        if set(iss["sides"]) != set(iss["action"]):
            E.append(f"issue {I}: sides and action letters differ")
        if iss["default"] not in iss["sides"]:
            E.append(f"issue {I}: default {iss['default']} is not a side")
        for s, cls in iss["action"].items():
            if cls not in acts:
                E.append(f"issue {I}: action class {cls} not defined in actions")
    for fid, f in (c.get("factors") or {}).items():
        if fid.startswith("cond."):
            E.append(f"factor {fid}: factor IDs may not use the condition prefix")
        if f["issue"] not in issues:
            E.append(f"factor {fid}: unknown issue {f['issue']}")
            continue
        if f["favors"] not in issues[f["issue"]]["sides"]:
            E.append(f"factor {fid}: favors {f['favors']} is not a side of {f['issue']}")
        maps = [("equities", f["equities"])]
        if "rungs" in f:
            if f.get("dimension") not in dims:
                E.append(f"factor {fid}: unknown dimension {f.get('dimension')}")
            else:
                order = dims[f["dimension"]]
                ks = list(f["rungs"])
                if any(k not in order for k in ks):
                    E.append(f"factor {fid}: rung not in dimension {f['dimension']}")
                elif ks != sorted(ks, key=order.index):
                    E.append(f"factor {fid}: rungs not in the dimension's order")
            for r, v in f["rungs"].items():
                if isinstance(v, dict):
                    maps.append((f"rung {r}", v))
                elif any(st != v for st in f["equities"].values()) and r == list(f["rungs"])[-1]:
                    W.append(f"factor {fid}: string rung strengths override the listed equity strengths "
                             f"(top rung {r} = {v}; listed {f['equities']})")
        for where, m in maps:
            for e, st in m.items():
                if e not in eqs:
                    E.append(f"factor {fid} ({where}): unknown equity {e}")
            vals = [S.STRENGTH[v] for v in m.values()]
            if len(vals) > 1 and max(vals[1:]) > vals[0] and not f.get("conjunctive"):
                E.append(f"factor {fid} ({where}): a secondary equity is stronger than the first (M2 lint); "
                         f"reorder or mark conjunctive: true")
        if f.get("mirror_of"):
            g = (c.get("factors") or {}).get(f["mirror_of"])
            if not g or g["issue"] != f["issue"] or g["favors"] == f["favors"] or g.get("dimension") != f.get("dimension"):
                E.append(f"factor {fid}: mirror_of must name an opposite-side factor on the same issue and dimension")
    for cls, a in acts.items():
        if a.get("tier") and a["tier"] not in tiers:
            E.append(f"action {cls}: unknown tier {a['tier']}")
        if a.get("direction") == "restrictive" and cls in (auth.get("non_delegable_to_agent") or []):
            E.append(f"action {cls}: restrictive classes are always within any role that can act (non_delegable)")
    for t, lvl in tiers.items():
        if lvl not in levels:
            E.append(f"tier {t}: level {lvl} not in levels")
        if t not in (c.get("stakes") or {}):
            E.append(f"tier {t}: no stakes (L, k)")
    for role, lvl in (auth.get("roles") or {}).items():
        if lvl is not None and lvl not in levels:
            E.append(f"role {role}: level {lvl} not in levels")
    if set(auth.get("inherent") or []) & set(auth.get("non_delegable_to_agent") or []):
        E.append("a class is both inherent and non_delegable_to_agent")
    cat = S.Catalog(doc, flags={f.get("flag") for f in (c.get("factors") or {}).values() if f.get("flag")})
    for t in (auth.get("tier_floors") or {}):
        if t not in cat.tag:
            E.append(f"tier_floors: {t} is not a factor tag (conditions never weigh or floor)")
    for rule in c.get("coupling") or []:
        for part in (rule["if"], rule["then"]):
            for I, s in part.items():
                if I not in issues or s not in issues[I]["sides"]:
                    E.append(f"coupling: {I}:{s} is not an issue side")
    return E, W


def _closed(cat, tags):
    return set(cat.close(tags)) == set(t for t in tags if cat.known(t))


def lint_record(cat, doc):
    """Record rules of spec 2 and the solver round trip. Returns (errors, warnings)."""
    r = doc.get("record", doc)
    E, W = [], []
    full = S.Catalog({"catalog": cat.raw}, flags={f.get("flag") for f in cat.all_factors.values() if f.get("flag")})
    if r["catalog"] != f"{cat.id}@{cat.version}":
        W.append(f"catalog reference {r['catalog']} != {cat.id}@{cat.version}")
    units = {u["id"] for u in r.get("units") or []}
    kind = (r.get("provenance") or {}).get("kind")
    ids, sit_tags, found = set(), set(), []
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
        if not _closed(full, [t for t in f["tags"] if full.known(t)]):
            E.append(f"fact {f['id']}: tags not closed downward {f['tags']}")
        if f["status"] == "assessed" and f.get("likelihood") not in LIKELIHOOD:
            E.append(f"fact {f['id']}: assessed facts need an ICD 203 likelihood")
        if f["status"] == "found" and f.get("known_at_decision", True):
            found.append(f["id"])
        if f.get("about") and f["about"] not in units:
            E.append(f"fact {f['id']}: about {f['about']} is not a unit")
        sit_tags |= set(full.close(f["tags"]))
    if found:
        (W if kind in ("adjudicated", "investigated") else E).append(
            f"facts {found}: status `found` in the situation layer (finder's perception; P1 leak if used held-out)")
    res = r["resolution"]
    for h in res["holdings"]:
        I = h["issue"]
        if I not in cat.issues:
            E.append(f"holding {I}: unknown issue")
            continue
        if h["outcome"] not in cat.sides(I):
            E.append(f"holding {I}: outcome {h['outcome']} is not a side")
        if h.get("unit") and h["unit"] not in units:
            E.append(f"holding {I}: unit {h['unit']} not listed")
        conds = [t for t in h["reason"] if t.startswith("cond.") or full.is_cond(t)]
        if conds:
            E.append(f"holding {I}: conditions never appear in a reason {conds}")
        ut = S.situation_from_record(full, r, h.get("unit"))["tags"]
        missing = set(full.close(h["reason"])) - ut
        if missing:
            E.append(f"holding {I}: reason not present at or above its rung in the situation {sorted(missing)}")
        wrong = [t for t in h["reason"] if full.known(t) and not full.is_cond(t) and
                 (full.issue_of(t) != I or full.side(t) != h["outcome"])]
        if wrong:
            W.append(f"holding {I}: reason factors off the issue or favoring the other side {wrong}")
    for fl in (r.get("guidance") or {}).get("flips") or []:
        tags = [c[1:] for c in fl["change"]]
        bad = [t for t in tags if not full.known(t)]
        if bad:
            E.append(f"flip {fl['id']}: change names unknown tags {bad}")
        if fl["then"]["issue"] not in cat.issues:
            E.append(f"flip {fl['id']}: unknown issue")
        if not r.get("units") and S.apply_change(full, sit_tags, fl["change"]) == sit_tags:
            W.append(f"flip {fl['id']}: change {fl['change']} is a no-op on this record's tags")
    for atom in res["plan"] + [a for o in r["situation"].get("options") or [] for a in o["plan"]]:
        I = atom.get("issue") or atom.get("then", {}).get("issue")
        if I not in cat.issues:
            E.append(f"plan atom {atom}: unknown issue")
        for cnd in atom.get("when") or []:
            if not cat.is_cond(cnd):
                E.append(f"plan atom: {cnd} is not a catalog condition")
    if E:
        return E, W
    cards = S.cards_from_record(cat, r)
    got = S.compose_record(cat, r, cards)
    if S.plan_atoms(got["plan"]) != S.plan_atoms(res["plan"]):
        E.append(f"gold plan not reproduced by solver_v3 from holdings + gate: solver {got['plan']}")
    for rt in res.get("routed") or []:
        a = got["actions"].get(rt["issue"])
        if a and a.get("because") and a["because"] != rt["because"]:
            W.append(f"routed {rt['issue']}: record says {rt['because']}, solver says {a['because']}")
    for bad in S.lint_horty(cat, cards):
        W.append(f"Horty/naqd lint: {bad['p'][0]} and {bad['q'][0]} both force opposite outcomes on {bad['Y']}")
    return E, W


def catalog_for(record_doc, catalogs):
    ref = record_doc["record"]["catalog"].split("@")[0]
    return catalogs.get(ref)


def main(paths):
    docs = {p: S.load_yaml(p) for p in paths}
    cats, nerr = {}, 0
    for p, d in docs.items():
        if "catalog" in d:
            E, W = schema_errors(d), []
            if not E:
                E, W = lint_catalog(d)
            cats[d["catalog"]["id"]] = S.Catalog(d, flags=("doctrine",))
            nerr += len(E)
            print(f"{'FAIL' if E else 'ok  '} {p}")
            for m in E: print("   E", m)
            for m in W: print("   W", m)
    for p, d in docs.items():
        if "record" in d:
            E, W = schema_errors(d), []
            cat = catalog_for(d, cats)
            if cat is None:
                E.append(f"no catalog loaded for {d['record']['catalog']}")
            elif not E:
                E, W = lint_record(cat, d)
            nerr += len(E)
            print(f"{'FAIL' if E else 'ok  '} {p}")
            for m in E: print("   E", m)
            for m in W: print("   W", m)
    return nerr


if __name__ == "__main__":
    args = sys.argv[1:] or sorted(glob.glob(os.path.join(HERE, "catalogs/*.yaml"))) + \
        sorted(glob.glob(os.path.join(HERE, "records/*.yaml")))
    sys.exit(1 if main(args) else 0)
