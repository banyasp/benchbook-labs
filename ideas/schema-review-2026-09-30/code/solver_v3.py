"""Solver v3 for Benchbook v7, spec v2 rules (drafts/SPEC-v7-v2.md, section 3). Pure Python + PyYAML.

Per issue I (and per unit, for unit-scoped holdings): 3.0 normalize (closure, established_by, data channel)
-> 3.1 gate (prohibitions, capped delegations, live orders, levels) -> 3.2 compare served cards (A5 effective
strength, reason_alts) -> 3.3 support (near-miss cards a half-step down, ceteris paribus) -> 3.4 stability over
extreme completions (a flag in either completion = contested) -> 3.5 compose (v2 rule order, interim, route `to`
lists, contingent, residue, duties). 3.6: derived guidance and lints. Round-1 file: code_r1/solver_v3.py.
Every choice the spec leaves open is marked "CHOICE" and listed in results/r2-results.md.
"""
import copy, glob, os
import yaml

RHO = 0.25
STRENGTH = {"weak": 1, "strong": 2}
FORCING = ("binding", "analogous")
VERDICT_RANK = {"binding": 3, "analogous": 2, "distinguished": 1, "off_point": 0}
NEW_AGAINST_EFFECTIVE = True     # A5, spec v2 3.2 default ON (round 1: off)
ORDER_LEVEL_CHECK = True         # CHOICE (converter g1): a live order authorizes only if its holder's level reaches
                                 # required_level(I, s); False = the literal v2 text


def p_star(L, k, rho=RHO):
    """The one act-or-route threshold (3.5 and 5): (L - k) / (1 + L - rho)."""
    return (L - k) / (1 + L - rho)


def load_yaml(path):
    with open(path) as fh:
        return yaml.safe_load(fh)


def as_list(x):
    return [] if x is None else (list(x) if isinstance(x, (list, tuple, set, frozenset)) else [x])


# ------------------------------------------------------------------------------------------------ catalog
SECTIONS = ("issues", "equities", "dimensions", "factors", "conditions", "actions")


def find_catalog(ref, search):
    """'CORE@2026-10' -> the catalog document with that id and version in any `search` directory."""
    cid, _, ver = ref.partition("@")
    for d in search:
        for p in sorted(glob.glob(os.path.join(d, "*.yaml"))):
            doc = load_yaml(p)
            c = (doc or {}).get("catalog") if isinstance(doc, dict) else None
            if c and c.get("id") == cid and (not ver or str(c.get("version")) == ver):
                return doc
    raise KeyError(f"catalog {ref} not found in {search}")


def merge_imports(doc, search, seen=()):
    """[v2] `imports`: imported sections first, the importing catalog's entries after (prohibitions are
    concatenated; authority, stakes, coupling come from the importer, falling back to an import).
    Returns (merged catalog dict, collisions)."""
    c = doc.get("catalog", doc)
    out = {k: {} for k in SECTIONS}
    out["prohibitions"], collisions = [], []
    for ref in c.get("imports") or []:
        if ref.partition("@")[0] in seen:
            raise ValueError(f"import cycle at {ref}")
        sub, col = merge_imports(find_catalog(ref, search), search, tuple(seen) + (c["id"],))
        collisions += col
        for k in SECTIONS:
            for key, v in sub[k].items():
                if key in out[k]:
                    collisions.append((k, key))
                out[k][key] = v
        out["prohibitions"] += sub["prohibitions"]
        for k in ("authority", "stakes", "coupling"):
            if sub.get(k) and not out.get(k):
                out[k] = sub[k]
    for k in SECTIONS:
        for key, v in (c.get(k) or {}).items():
            if key in out[k]:
                collisions.append((k, key))
            out[k][key] = v
    out["prohibitions"] += c.get("prohibitions") or []
    for k in ("authority", "stakes", "coupling"):
        if c.get(k):
            out[k] = c[k]
    for k in c:
        if k not in out and k not in ("imports",):
            out[k] = c[k]
    return out, collisions


class Catalog:
    """A v7 catalog (spec 1) plus derived indices. Tags: 'ID', 'ID@rung' or a condition id ('cond.*').
    `flags` switches on factors carrying `flag:` (the DOHA doctrine extension); `search` resolves imports."""

    def __init__(self, doc, flags=(), search=()):
        c, self.collisions = merge_imports(doc, list(search))
        self.raw, self.flags = c, set(flags)
        self.id, self.version = c["id"], str(c.get("version", ""))
        self.issues = c["issues"]
        self.equity_defs = c.get("equities") or {}
        dims = c.get("dimensions") or {}
        self.dimensions = {d: (v["rungs"] if isinstance(v, dict) else v) for d, v in dims.items()}
        self.dim_mirror = {d: bool(isinstance(v, dict) and v.get("mirror")) for d, v in dims.items()}
        self.conditions = c.get("conditions") or {}
        self.actions = c.get("actions") or {}
        self.auth = c.get("authority") or {}
        self.stakes = c.get("stakes") or {}
        self.coupling = c.get("coupling") or []
        self.prohibitions = c.get("prohibitions") or []
        self.all_factors = c.get("factors") or {}
        self.factors = {k: v for k, v in self.all_factors.items() if not v.get("flag") or v["flag"] in self.flags}
        self.tag, self.ladder = {}, {}       # tag -> (stem, rung, closure index); stem -> tags in closure order
        for fid, f in self.factors.items():
            if "rungs" in f:
                order = self.dimensions[f["dimension"]]
                rungs = sorted(f["rungs"], key=order.index)
                if f.get("mirror_of"):          # CHOICE (r1): a mirror face reads "value <= r" and closes upward
                    rungs = rungs[::-1]
                self.ladder[fid] = [f"{fid}@{r}" for r in rungs]
                for i, r in enumerate(rungs):
                    self.tag[f"{fid}@{r}"] = (fid, r, i)
            else:
                self.ladder[fid] = [fid]
                self.tag[fid] = (fid, None, 0)
        self.levels = self.auth.get("levels") or []
        self.tiers = self.auth.get("tiers") or {}
        self.tier_order = list(self.tiers)

    def known(self, t):
        return t in self.tag or t in self.conditions

    def is_cond(self, t):
        return t in self.conditions

    def stem(self, t):
        return self.tag[t][0]

    def fac(self, t):
        return self.factors[self.tag[t][0]]

    def side(self, t):
        return self.fac(t)["favors"] if t in self.tag else None

    def issue_of(self, t):
        return self.fac(t)["issue"] if t in self.tag else None

    def knockout(self, t):
        return bool(self.fac(t).get("knockout"))

    def equities(self, t):
        """equity -> strength. [v2] a scaled factor's rung strength governs every listed equity (list form);
        a dict rung value gives per-equity strengths (SEC-F A20d)."""
        f, r = self.fac(t), self.tag[t][1]
        names = f["equities"]
        if r is None:
            return dict(names) if isinstance(names, dict) else {e: "strong" for e in names}
        spec = f["rungs"][r]
        return dict(spec) if isinstance(spec, dict) else {e: spec for e in names}

    def on_issue(self, tags, issue):
        return {t for t in tags if t in self.tag and self.issue_of(t) == issue}

    def close(self, tags):
        """3.0: drop unknown tags; a rung tag implies every lower rung of the same factor."""
        out = set()
        for t in tags:
            if t in self.conditions:
                out.add(t)
            elif t in self.tag:
                out.update(self.ladder[self.stem(t)][: self.tag[t][2] + 1])
        return out

    def top(self, tags):
        """stem -> highest present tag (the observed rung)."""
        best = {}
        for t in tags:
            if t in self.tag:
                s = self.stem(t)
                if s not in best or self.tag[t][2] > self.tag[best[s]][2]:
                    best[s] = t
        return best

    def sides(self, issue):
        return list(self.issues[issue]["sides"])

    def other(self, issue, s):
        a, b = self.sides(issue)
        return b if s == a else a

    def klass(self, issue, s):
        return self.issues[issue]["action"][s]

    def restrictive(self, cls):
        return self.actions.get(cls, {}).get("direction") == "restrictive"

    def reversible(self, cls):
        return self.actions.get(cls, {}).get("reversible", True)

    def tier_max(self, tiers):
        tiers = [t for t in tiers if t]
        return max(tiers, key=self.tier_order.index) if tiers else None

    def tier_bump(self, tier, n):
        i = min(self.tier_order.index(tier) + n, len(self.tier_order) - 1)
        return self.tier_order[i]

    def stake(self, tier):
        s = self.stakes.get(tier or self.tier_order[0]) or {"L": 1, "k": 0.2}
        return s["L"], s["k"]

    def l_max(self):
        return max((v["L"] for v in self.stakes.values()), default=1)

    def level_rank(self, lvl):
        return self.levels.index(lvl) if lvl in self.levels else None


def load_catalog(path, flags=(), search=None):
    return Catalog(load_yaml(path), flags, search or [os.path.dirname(os.path.abspath(path))])


# ------------------------------------------------------------------------------------------------ records (3.0)
def _unit_class(r, unit):
    for u in r.get("units") or []:
        if u.get("id") == unit:
            return u.get("class", unit)
    return None


def condition_ok(cat, fact, c):
    """[v2] 3.0 / P7: a condition tag survives only if its carrier is not on the data channel and, when the
    catalog gives `established_by`, the fact names that holder in `by:` with the required `form`."""
    if fact.get("channel") == "data":
        return False, "data channel cannot establish a condition"
    est = cat.conditions[c].get("established_by")
    if not est:
        return True, None
    for e in est:
        if fact.get("by") == e.get("holder") and e.get("form", "any") in ("any", None, fact.get("form")):
            return True, None
    return False, f"established_by {est} not met (by={fact.get('by')}, form={fact.get('form')})"


def _uncertain(cat, s):
    """situation.uncertain: [v2] a list of {tag, values} or (r1) a map {stem or condition: values}."""
    u = s.get("uncertain") or {}
    if isinstance(u, dict):
        return {k: list(v) for k, v in u.items()}
    out = {}
    for e in u:
        t = e["tag"]
        out[t if cat.is_cond(t) else t.split("@")[0]] = list(e["values"])
    return out


def situation_from_record(cat, rec, unit=None):
    """The decision-point layer (P1) as solver input. CHOICE: facts with status `rejected`,
    `known_at_decision: false` or `use: credibility_only` add no tags; a `disputed` fact's tags become
    uncertain; with `unit`, only facts about that unit or about no unit count (unit=None: all facts)."""
    r = rec.get("record", rec)
    s = r["situation"]
    tags, unc, dropped = set(), {}, []
    for f in s.get("facts") or []:
        if unit is not None and f.get("about") is not None and unit not in as_list(f.get("about")):
            continue
        if f.get("status") == "rejected" or f.get("known_at_decision") is False or f.get("use") == "credibility_only":
            continue
        ft = set()
        for t in cat.close(f.get("tags") or []):
            if cat.is_cond(t):
                ok, why = condition_ok(cat, f, t)
                if not ok:
                    dropped.append((f["id"], t, why))
                    continue
            ft.add(t)
        if f.get("status") == "disputed":
            for stem, t in cat.top(ft).items():
                lad = cat.ladder[stem]
                unc[stem] = ["absent"] + [x.split("@")[-1] if "@" in x else "present" for x in lad[: cat.tag[t][2] + 1]]
            unc.update({c: ["absent", "present"] for c in ft if cat.is_cond(c)})
        else:
            tags |= ft
    unc.update(_uncertain(cat, s))
    return {"tags": tags, "uncertain": unc, "agent": s.get("agent") or {}, "authority": s.get("authority") or {},
            "unit": unit, "unit_class": _unit_class(r, unit), "record_id": r["id"], "dropped": dropped}


def _base(r):
    prov = (r.get("provenance") or {}).get("authority") or {}
    return {"id": r["id"], "status": prov.get("status", "current"), "rank": prov.get("rank") or 0,
            "requires": frozenset(), "forbids": frozenset(), "scope": frozenset(), "route": None}


def _units_tags(cat, r, units):
    if not units:
        return situation_from_record(cat, r)["tags"]
    out = set()
    for u in units:
        out |= situation_from_record(cat, r, u)["tags"]
    return out


def cards_from_record(cat, rec, with_flips=True):
    """Exemplar cards: one per holding ([v2] `units`, `reason_alts`), plus each typed flip compiled to
    near-miss cards (3.6) ranked a half-step below the base (A4)."""
    r = rec.get("record", rec)
    base = _base(r)
    cards = []
    for h in (r.get("resolution") or {}).get("holdings") or []:
        units = as_list(h.get("units") or h.get("unit"))
        alts = [frozenset(cat.close(a)) for a in (h.get("reason_alts") or [h.get("reason") or []])]
        cards.append(dict(base, issue=h["issue"], units=frozenset(units) or None,
                          unit_classes=frozenset(_unit_class(r, u) for u in units) or None,
                          outcome=h["outcome"], alts=alts, reason=frozenset().union(*alts),
                          X=frozenset(_units_tags(cat, r, units)), force=h.get("force", "required"), kind="holding"))
    if with_flips:
        for fl in (r.get("guidance") or {}).get("flips") or []:
            cards += compile_flip(cat, r, fl, base)
    return cards


def _change(fl):
    ch = fl.get("change") or {}
    if isinstance(ch, list):          # r1 grammar: ["+T", "-T"]
        return {"add": [c[1:] for c in ch if c[0] == "+"], "remove": [c[1:] for c in ch if c[0] == "-"]}
    return ch


def _remove_tags(cat, tags, rem):
    out = set(tags)
    for t in rem:
        if t in cat.tag:
            out -= set(cat.ladder[cat.stem(t)][cat.tag[t][2]:])
        else:
            out.discard(t)
    return out


def apply_change(cat, tags, change):
    """X (+) change on a tag set. change: r1 list ['+T', '-T'] or v2 {add, remove}."""
    ch = _change({"change": change})
    return cat.close(_remove_tags(cat, tags, ch.get("remove") or [])) | cat.close(ch.get("add") or [])


def apply_flip(cat, rec, fl):
    """[v2] H10 grammar applied to a record: replace_fact, then remove/add (per unit with `about`), add_order.
    CHOICE: added tags ride on a synthetic fact whose `by`/`form` come from the flip's (non-spec) actor/form."""
    d = copy.deepcopy(rec if "record" in rec else {"record": rec})
    r = d["record"]
    s = r["situation"]
    ch = _change(fl)
    about = ch.get("about")
    if ch.get("replace_fact"):
        rf = ch["replace_fact"]
        s["facts"] = [dict(rf["with"]) if f["id"] == rf["id"] else f for f in s["facts"]]
    facts = []
    for f in s["facts"]:
        ab = as_list(f.get("about"))
        if about is not None and about not in ab:
            facts.append(f)
            continue
        if about is not None and len(ab) > 1:          # split a multi-unit fact: the change is about one unit
            facts.append(dict(f, about=[u for u in ab if u != about]))
            f = dict(f, id=f"{f['id']}:{about}", about=[about])
        facts.append(dict(f, tags=sorted(_remove_tags(cat, cat.close(f.get("tags") or []), ch.get("remove") or []))))
    s["facts"] = facts
    if ch.get("add"):
        s["facts"].append({"id": f"flip:{fl.get('id')}", "text": "(flip)", "status": "observed",
                           "channel": "principal" if fl.get("actor") else "sensor", "about": about,
                           "by": fl.get("actor"), "form": fl.get("form"), "tags": list(ch["add"])})
    touched = {t if cat.is_cond(t) else t.split("@")[0] for t in (ch.get("add") or []) + (ch.get("remove") or [])}
    u = s.get("uncertain")
    if u:                                   # a flip that adds or removes an uncertain tag resolves it
        s["uncertain"] = {k: v for k, v in u.items() if k not in touched} if isinstance(u, dict) else \
            [e for e in u if (e["tag"] if cat.is_cond(e["tag"]) else e["tag"].split("@")[0]) not in touched]
    if ch.get("add_order"):
        s.setdefault("authority", {}).setdefault("orders", [])
        s["authority"]["orders"] = list(s["authority"]["orders"]) + [ch["add_order"]]
    return d


def compile_flip(cat, r, fl, base):
    """3.6: a typed flip -> near-miss cards, one per `then` clause. [v2] rank = base - 0.5; applies only
    ceteris paribus (A4): scope = (base X's tags on the issue favoring the base outcome, minus what the change
    removes) plus what it adds; added conditions are required, removed ones forbidden.
    CHOICE: a flip whose change adds an order is a holder's decision, not a world fact; it is not compiled."""
    ch = _change(fl)
    if ch.get("add_order"):
        return []
    r2 = apply_flip(cat, r, fl)["record"]
    holds = {(h["issue"], u): h["outcome"] for h in (r.get("resolution") or {}).get("holdings") or []
             for u in (as_list(h.get("units")) or [None])}
    clauses = as_list(fl.get("then"))
    out = []
    for n, th in enumerate(clauses):
        I = th["issue"]
        units = as_list(th.get("units")) or [None]      # `about` scopes the change, not the result
        for u in units:
            X = situation_from_record(cat, r, u)["tags"]
            Xp = situation_from_record(cat, r2, u)["tags"]
            add, rem = Xp - X, X - Xp
            ob = holds.get((I, u), holds.get((I, None), th.get("outcome")))
            scope = ({t for t in cat.on_issue(X, I) if cat.side(t) == ob} - rem) | cat.on_issue(add, I)
            card = dict(base, id=f"{r['id']}/{fl.get('id')}" + (f"#{n}" if len(clauses) > 1 else ""), issue=I,
                        units=frozenset([u]) if u else None,
                        unit_classes=frozenset([_unit_class(r, u)]) if u else None, X=frozenset(Xp), kind="flip",
                        rank=base["rank"] - 0.5, force=th.get("force", "required"), scope=frozenset(scope),
                        requires=frozenset(c for c in add if cat.is_cond(c)),
                        forbids=frozenset(c for c in rem if cat.is_cond(c)))
            if th.get("route"):
                card.update(outcome=None, route=th["route"], alts=[frozenset()], reason=frozenset())
            elif th.get("outcome"):
                o = th["outcome"]
                R = [t for t in (fl.get("reason") or []) if cat.known(t) and cat.issue_of(t) == I] or \
                    [t for t in cat.on_issue(Xp, I) if cat.side(t) == o]
                card.update(outcome=o, alts=[frozenset(cat.close(R))], reason=frozenset(cat.close(R)))
            else:
                continue
            out.append(card)
    return out


# ------------------------------------------------------------------------------------------------ 3.1 gate
def _auth(sit, key):
    return (sit.get("authority") or {}).get(key) or []


def holders_of(sit, cls):
    return [d["holder"] for d in _auth(sit, "deciders") if cls in (d.get("holds") or [])]


def level_of(sit, holder):
    return next((d.get("level") for d in _auth(sit, "deciders") if d["holder"] == holder and d.get("level")), None)


def delegation_active(sit, d, tags):
    """Active iff every `when` condition is present in every completion (an uncertain one never activates)."""
    return all(c in tags and c not in sit.get("uncertain", {}) for c in d.get("when") or [])


def prohibited_classes(cat, tags):
    """[v2] H3: a prohibition whose `when` holds and whose `unless` does not forbids its action for every holder."""
    out = {}
    for p in cat.prohibitions:
        if all(c in tags for c in p.get("when") or []) and not any(c in tags for c in p.get("unless") or []):
            out[p["forbids"]["action"]] = p.get("id")
    return out


def _floors(cat, issue, tags):
    return {k: v for k, v in (cat.auth.get("tier_floors") or {}).items() if k in tags and cat.issue_of(k) == issue}


def required_tier(cat, issue, s, tags):
    """(level tier, stakes tier) of side s: max of the class tier and present tier floors on the issue
    (permissive only; a restrictive class needs no level, its declared tier is kept for stakes)."""
    cls = cat.klass(issue, s)
    t = cat.actions.get(cls, {}).get("tier")
    if cat.restrictive(cls):
        return None, t
    t = cat.tier_max([t] + list(_floors(cat, issue, tags).values())) or cat.tier_order[0]
    return t, t


def issue_tier(cat, issue, tags, settled=True):
    """[v2] A1 + H9: max over both sides, +irreversible_bump when the permissive action is irreversible and
    the issue is unsettled."""
    t = cat.tier_max([required_tier(cat, issue, s, tags)[1] for s in cat.sides(issue)]) or cat.tier_order[0]
    bump = cat.auth.get("irreversible_bump") or 0
    if not settled and bump and any(not cat.restrictive(cat.klass(issue, s)) and not cat.reversible(cat.klass(issue, s))
                                    for s in cat.sides(issue)):
        t = cat.tier_bump(t, bump)
    return t


def order_state(cat, sit, od, tags, forbidden):
    """[v2] live | inactive (active_when unmet) | disabled (disabled_by present, or its side prohibited) |
    superseded (quietly ignored)."""
    I, s = od["directs"]["issue"], od["directs"]["side"]
    if not all(c in tags for c in od.get("active_when") or []):
        return "inactive"
    if any(c in tags for c in od.get("superseded_by") or []):
        return "superseded"
    if any(c in tags for c in od.get("disabled_by") or []) or cat.klass(I, s) in forbidden:
        return "disabled"
    return "live"


def _orders_for(sit, issue):
    u = sit.get("unit")
    return [od for od in _auth(sit, "orders") if od["directs"]["issue"] == issue and
            (u is None or not od["directs"].get("units") or u in od["directs"]["units"])]


def order_effects(cat, sit, issue, tags, forbidden=None):
    """Exclusions (factors AGAINST the directed side whose equities all fall in `excludes`, only while
    `excludes_when` holds; A8, H2c), whether a disabled order raises a flag, and the live orders."""
    forbidden = prohibited_classes(cat, tags) if forbidden is None else forbidden
    excl, flag, live = set(), False, []
    for od in _orders_for(sit, issue):
        st = order_state(cat, sit, od, tags, forbidden)
        if st == "disabled":
            flag = True
        if st != "live":
            continue
        live.append(od)
        if all(c in tags for c in od.get("excludes_when") or []) and od.get("excludes"):
            ex, s = set(od["excludes"]), od["directs"]["side"]
            excl |= {t for t in cat.on_issue(tags, issue) if cat.side(t) != s and set(cat.equities(t)) <= ex}
    return excl, flag, live


def unreachable_holders(cat, sit, tags):
    return {cat.conditions[c].get("unreachable") for c in tags
            if cat.is_cond(c) and c not in sit.get("uncertain", {}) and cat.conditions[c].get("unreachable")}


def route_to(cat, sit, cls, tags):
    """[v2] H8: the delegatee(s) whose delegation of the class is active and reachable, else every holder."""
    down = unreachable_holders(cat, sit, tags)
    dele = [d["to"] for d in _auth(sit, "delegations") if cls in (d.get("holds") or []) and d.get("to", "agent") != "agent"
            and delegation_active(sit, d, tags) and d["to"] not in down]
    return dele or holders_of(sit, cls) or [sit["agent"].get("serves")]


def gate(cat, sit, issue, tags):
    """3.1 per issue: side -> {within, class, holders, tier, prohibited, via}. `tags` are the completion being
    gated, after order exclusions (removed factors take their floors with them)."""
    lvl = (cat.auth.get("roles") or {}).get(sit["agent"].get("role", "none"))
    forbidden = prohibited_classes(cat, tags)
    _, _, live = order_effects(cat, sit, issue, tags, forbidden)
    floors = _floors(cat, issue, tags)
    out = {}
    for s in cat.sides(issue):
        cls = cat.klass(issue, s)
        need, _ = required_tier(cat, issue, s, tags)
        base_t = cat.actions.get(cls, {}).get("tier")
        raising = [k for k, v in floors.items() if base_t is None or cat.tier_order.index(v) > cat.tier_order.index(base_t)]
        via = None
        if cls in forbidden:
            via = f"prohibited ({forbidden[cls]})"
        elif cls in (cat.auth.get("non_delegable_to_agent") or []):
            via = "non-delegable"
        elif cat.restrictive(cls):
            via = "restrictive"
        elif cls in (cat.auth.get("inherent") or []):
            via = "inherent"
        elif any(cls in (d.get("holds") or []) and d.get("to", "agent") == "agent" and delegation_active(sit, d, tags)
                 and set(raising) <= set(d.get("covers_floors") or []) for d in _auth(sit, "delegations")):
            via = "delegation"                                          # H1: floors cap delegations
        elif any(od["directs"]["side"] == s and od.get("from") in holders_of(sit, cls) and
                 (not ORDER_LEVEL_CHECK or level_of(sit, od["from"]) is None or need is None or
                  cat.level_rank(level_of(sit, od["from"])) >= cat.level_rank(cat.tiers[need])) for od in live):
            via = "order"                                               # H2a (+ level check, CHOICE g1)
        elif lvl is not None and need is not None and cat.level_rank(lvl) >= cat.level_rank(cat.tiers[need]):
            via = "level"
        within = via in ("restrictive", "inherent", "delegation", "order", "level")
        out[s] = {"within": within, "class": cls, "holders": route_to(cat, sit, cls, tags), "tier": need,
                  "prohibited": cls in forbidden, "via": via}
    return out


def gate_result(cat, sit, issue, tags):
    """The WHO-block summary scored by r_who ([v2] section 4): ('within', (), None) if every non-prohibited
    side is within role, else ('route', holders of the out-of-role side, interim restrictive side)."""
    Y = set(tags) - order_effects(cat, sit, issue, tags)[0]
    g = gate(cat, sit, issue, Y)
    out = [s for s in cat.sides(issue) if not g[s]["within"] and not g[s]["prohibited"]]
    if not out:
        return ("within", (), None)
    return ("route", tuple(sorted(g[out[0]]["holders"])), interim_side(cat, issue, g))


def interim_side(cat, issue, g):
    """[v2] P4: the restrictive side held while a permissive side is routed. CHOICE: if both sides are
    restrictive, the catalog default; none if no restrictive side is within role."""
    rs = [s for s in cat.sides(issue) if cat.restrictive(g[s]["class"]) and g[s]["within"]]
    if len(rs) > 1:
        d = cat.issues[issue]["default"]
        return d if d in rs else rs[0]
    return rs[0] if rs else None


# ------------------------------------------------------------------------------------------------ 3.2
def effective(cat, t, facts, e):
    """solver_v2's blocking: strong -> 2; weak -> 1, or 0 when the same fact set (same issue) holds an
    opposing-side factor with strong support on e; absent equity -> 0."""
    st = cat.equities(t).get(e)
    if st is None:
        return 0
    if st == "strong":
        return 2
    s, I = cat.side(t), cat.issue_of(t)
    return 0 if any(g in cat.tag and cat.issue_of(g) == I and cat.side(g) != s and cat.equities(g).get(e) == "strong"
                    for g in facts) else 1


def mirror_set(cat, R, o):
    """Horty 2021 Def. 9, factor form (only for dimensions with `mirror: true`)."""
    out = set()
    for t in R:
        if t not in cat.tag or cat.tag[t][1] is None:
            continue
        f, r = cat.fac(t), cat.tag[t][1]
        dim = f["dimension"]
        if not cat.dim_mirror.get(dim):
            continue
        order = cat.dimensions[dim]
        for gid, g in cat.factors.items():
            if (g.get("mirror_of") == cat.stem(t) or f.get("mirror_of") == gid) and g.get("favors") != o \
                    and g.get("dimension") == dim:
                out |= {f"{gid}@{x}" for x in g["rungs"] if order.index(x) >= order.index(r)}
    return out


def _covered(cat, d, pool, facts, e, need):
    return any(cat.stem(g) != cat.stem(d) and effective(cat, g, facts, e) >= need for g in pool)


def applies(card, Y):
    """[v2] A4: a near-miss card applies only ceteris paribus (its scope present) and with its conditions."""
    Y = set(Y)
    return card["requires"] <= Y and not card["forbids"] & Y and card.get("scope", frozenset()) <= Y


def _compare_one(cat, I, o, R, X, Y):
    ob = cat.other(I, o)
    Yo = {t for t in Y if cat.side(t) == o}
    Xob = {t for t in X if cat.side(t) == ob}
    mir = mirror_set(cat, R, o)
    missing = sorted(t for s, t in cat.top(R).items() if t not in Y)
    new = sorted(cat.top({t for t in Y if cat.side(t) == ob and t not in Xob and t not in mir}).values())
    unc = {}
    for d in missing:
        unc[d] = [e for e, st in cat.equities(d).items() if not _covered(cat, d, Yo, Y, e, STRENGTH[st])]
    for d in new:
        need = {e: (effective(cat, d, Y, e) if NEW_AGAINST_EFFECTIVE else STRENGTH[st]) for e, st in cat.equities(d).items()}
        unc[d] = [e for e in need if need[e] and not _covered(cat, d, Xob, X, e, need[e])]
    sig = sorted(d for d in missing + new if unc[d] or cat.knockout(d))
    rstems = {cat.stem(t) for t in R}
    present = any(cat.stem(t) in rstems for t in Y)
    any_cov = any(_covered(cat, t, Yo, Y, e, STRENGTH[st]) for t in cat.top(R).values()
                  for e, st in cat.equities(t).items())
    if not present and not any_cov:
        return {"verdict": "off_point", "missing": [], "new": [], "significant": [], "uncovered": {}}
    v = "binding" if not missing and not new else ("distinguished" if sig else "analogous")
    return {"verdict": v, "missing": missing, "new": new, "significant": sig, "uncovered": unc}


def compare(cat, card, Y):
    """3.2: one card against situation tags Y. [v2] reason_alts: keep the alternative with the fewest
    significant distinctions (so a missing reason exists only if every alternative misses something)."""
    if not applies(card, Y):
        return {"verdict": "off_point", "missing": [], "new": [], "significant": [], "uncovered": {},
                "note": "out of scope or conditions unmet"}
    I = card["issue"]
    Yi, X = cat.on_issue(Y, I), cat.on_issue(card["X"], I)
    best = None
    for R in card.get("alts") or [card["reason"]]:
        r = _compare_one(cat, I, card["outcome"], cat.on_issue(R, I), X, Yi)
        key = (r["verdict"] == "off_point", len(r["significant"]), len(r["missing"]) + len(r["new"]))
        if best is None or key < best[0]:
            best = (key, r)
    return best[1]


# ------------------------------------------------------------------------------------------------ 3.3
def card_key(c):
    return (c["id"], c["issue"], tuple(sorted(c["units"])) if c.get("units") else None)


def _card_fits(c, sit):
    """Per-unit holdings compare only against a situation about a unit of the same class ([v2] 3.2)."""
    if not c.get("units"):
        return True
    u = sit.get("unit")
    if u is None:
        return False
    if c["id"].split("/")[0] == sit.get("record_id"):
        return u in c["units"]
    return sit.get("unit_class") in (c.get("unit_classes") or ())


def support(cat, cards, Y, issue, sit=None):
    """3.3 over the served cards only: {status: settled|bounded|open|unprecedented, side, label, route,
    permissible, verdicts}. Near-miss cards carry rank - 0.5 (A4)."""
    sit = sit or {}
    live = [c for c in cards if c["issue"] == issue and _card_fits(c, sit)
            and c.get("status", "current") == "current" and c.get("force", "required") in ("required", "permitted")]
    verdicts, route, forcing, permissible, on_point = {}, None, {}, set(), set()
    for c in live:
        if c.get("route"):
            ok = applies(c, Y)
            verdicts[card_key(c)] = {"verdict": "applies" if ok else "off_point", "route": c["route"]}
            route = route or (c["route"] if ok else None)
            continue
        r = compare(cat, c, Y)
        verdicts[card_key(c)] = r
        v, o = r["verdict"], c["outcome"]
        if v in FORCING and c.get("force", "required") == "required":
            cand = (c.get("rank", 0), VERDICT_RANK[v])
            forcing[o] = max(forcing[o], cand) if o in forcing else cand
        elif v in FORCING:
            permissible.add(o)
            on_point.add(o)
        elif v == "distinguished":
            on_point.add(o)
    res = {"route": route, "verdicts": verdicts, "permissible": permissible, "side": None, "label": None}
    if len(forcing) == 2:
        (s1, r1), (s2, r2) = sorted(forcing.items(), key=lambda kv: -kv[1][0])
        if r1[0] == r2[0]:
            return dict(res, status="bounded")
        forcing = {s1: r1}
    if len(forcing) == 1:
        (s, (rk, vr)), = forcing.items()
        return dict(res, status="settled", side=s, label="binding" if vr == 3 else "analogous",
                    permissible=permissible | {s})
    return dict(res, status={2: "bounded", 1: "open", 0: "unprecedented"}[len(on_point)])


# ------------------------------------------------------------------------------------------------ 3.4
def _value_tags(cat, u, v):
    if v in (None, "absent"):
        return set()
    if cat.is_cond(u):
        return {u}
    return {cat.ladder[u][0]} if v == "present" else cat.close([f"{u}@{v}"])


def _vkey(cat, u, v):
    if v in (None, "absent"):
        return -1
    return 0 if (v == "present" or cat.is_cond(u)) else cat.tag[f"{u}@{v}"][2]


def _relevant(cat, sit, issue):
    return {u: vs for u, vs in sit["uncertain"].items()
            if cat.is_cond(u) or (u in cat.factors and cat.factors[u]["issue"] == issue)}


def _helps(cat, sit, issue, side, c):
    """CHOICE: an uncertain condition's direction for `side` from the v2 authority constructs."""
    mine, theirs = cat.klass(issue, side), cat.klass(issue, cat.other(issue, side))
    sc = 0
    for d in _auth(sit, "delegations"):
        if c in (d.get("when") or []):
            sc += (mine in (d.get("holds") or [])) - (theirs in (d.get("holds") or []))
    for od in _orders_for(sit, issue):
        sgn = 1 if od["directs"]["side"] == side else -1
        sc += sgn * ((c in (od.get("active_when") or [])) + (c in (od.get("excludes_when") or []))
                     - (c in (od.get("disabled_by") or [])) - (c in (od.get("superseded_by") or [])))
    for p in cat.prohibitions:
        sgn = -1 if p["forbids"]["action"] == mine else (1 if p["forbids"]["action"] == theirs else 0)
        sc += sgn * ((c in (p.get("when") or [])) - (c in (p.get("unless") or [])))
    return sc


def completion(cat, sit, issue, side, fixed=None):
    """3.4: the most-`side` completion of `issue` (Odekerken, Bex & Prakken 2023): uncertain factor stems
    favoring `side` at their highest value, others at their lowest; an uncertain condition present iff it
    helps `side` (delegation `when`, order `active_when`, prohibition `when`/`unless`, ...)."""
    fixed = fixed or {}
    unc = _relevant(cat, sit, issue)
    tags = set(sit["tags"])
    for u in unc:
        tags -= set(cat.ladder.get(u, [u]))
    for u, vals in unc.items():
        key = lambda x: _vkey(cat, u, x)
        if u in fixed:
            v = fixed[u]
        elif cat.is_cond(u):
            v = max(vals, key=key) if _helps(cat, sit, issue, side, u) > 0 else min(vals, key=key)
        else:
            v = (max if cat.factors[u]["favors"] == side else min)(vals, key=key)
        tags |= _value_tags(cat, u, v)
    return tags


def _run(cat, cards, sit, issue, tags):
    s0 = dict(sit, tags=tags, uncertain={})
    excl, oflag, _ = order_effects(cat, s0, issue, tags)
    Y = set(tags) - excl
    return dict(support(cat, cards, Y, issue, s0), gate=gate(cat, s0, issue, Y), flag=oflag, tags=Y)


def _stable(cat, a, b, issue):
    return (a["status"] == b["status"] == "settled" and a["side"] == b["side"] and a["route"] == b["route"]
            and all(a["gate"][s]["within"] == b["gate"][s]["within"] for s in cat.sides(issue)))


def assess(cat, cards, sit, issue, fixed=None):
    """3.3 + 3.4 for one issue. Stable iff both extreme completions settle the same side with the same gate.
    [v2] A flag in either completion flags the issue (H7: contested = the completions disagree on the route
    reason). Unstable -> 'unstable', U* = uncertain items whose resolution alone (to either extreme) makes
    the issue stable; the gate is the conservative AND of both completions."""
    unc = {u: v for u, v in _relevant(cat, sit, issue).items() if u not in (fixed or {})}
    if not unc:
        return dict(_run(cat, cards, sit, issue, completion(cat, sit, issue, cat.sides(issue)[0], fixed)),
                    stable=True, ustar=[], contested=False)
    ext = [_run(cat, cards, sit, issue, completion(cat, sit, issue, s, fixed)) for s in cat.sides(issue)]
    flag = ext[0]["flag"] or ext[1]["flag"]
    contested = ext[0]["flag"] != ext[1]["flag"]
    g = {s: dict(ext[0]["gate"][s], within=ext[0]["gate"][s]["within"] and ext[1]["gate"][s]["within"],
                 prohibited=ext[0]["gate"][s]["prohibited"] or ext[1]["gate"][s]["prohibited"])
         for s in cat.sides(issue)}
    if _stable(cat, ext[0], ext[1], issue):
        return dict(ext[0], gate=g, flag=flag, contested=contested, stable=True, ustar=[])
    ustar = []
    if fixed is None:
        for u, vals in unc.items():
            lo, hi = (f(vals, key=lambda x: _vkey(cat, u, x)) for f in (min, max))
            if all(assess(cat, cards, sit, issue, {u: v})["stable"] for v in (lo, hi)):
                ustar.append(u)
    return dict(ext[0], status="unstable", side=None, label=None, gate=g, stable=False, ustar=sorted(ustar),
                flag=flag, contested=contested, route=ext[0]["route"] or ext[1]["route"])


# ------------------------------------------------------------------------------------------------ 3.5
def issues_in_play(cat, cards, sit, pi=None, flags=(), contested=()):
    """CHOICE: issues with a situation tag, a fitting served card, an order, a distribution or a flag."""
    out = {cat.issue_of(t) for t in sit["tags"] if t in cat.tag}
    out |= {cat.factors[u]["issue"] for u in sit["uncertain"] if u in cat.factors}
    out |= {c["issue"] for c in cards if _card_fits(c, sit)} | {od["directs"]["issue"] for od in _auth(sit, "orders")}
    out |= set(k.split("[")[0] for k in (pi or {})) | {f["issue"] for f in flags} | set(contested)
    return [I for I in cat.issues if I in out]


def _argmax(dist, allowed):
    dist = {s: p for s, p in (dist or {}).items() if s in allowed}
    if not dist:
        return None, None
    s = max(sorted(dist), key=lambda k: dist[k])
    return s, dist[s]


def compose_issue(cat, cards, sit, issue, pi=None, flagged=False):
    """3.5, v2 rule order, for one issue (one unit) -> (action, assessment)."""
    a = assess(cat, cards, sit, issue)
    g, sides, tags = a["gate"], cat.sides(issue), a["tags"]
    avail = [s for s in sides if not g[s]["prohibited"]]                       # rule 1
    interim = interim_side(cat, issue, g)
    s_star, p = _argmax(pi, avail)
    perm = next((s for s in sides if not cat.restrictive(g[s]["class"])), sides[0])

    def route(because, side, rec, **kw):
        act = dict(act="route", issue=issue, side=side, because=because, to=list(g[side]["holders"]), recommend=rec, **kw)
        return act if interim is None or interim == side else dict(act, interim=interim)

    settled = a["status"] == "settled" and a["side"] in avail
    if flagged or a["flag"]:                                                   # rule 2
        act = route("flag", perm, s_star)
    elif a["route"]:                                                           # an applicable route card
        act = route(a["route"], perm, a["side"] or s_star)
    elif settled and g[a["side"]]["within"]:                                   # rule 3
        act = dict(act="proceed", issue=issue, side=a["side"])
    elif settled:                                                              # rule 4
        act = route("authorize", a["side"], a["side"])
    elif [s for s in avail if not g[s]["within"]]:                             # rule 5
        act = route("authorize", [s for s in avail if not g[s]["within"]][0], s_star)
    elif len(avail) == 1:                     # CHOICE: the other side is prohibited; the sole lawful side proceeds
        act = dict(act="proceed", issue=issue, side=avail[0])
    elif s_star is not None and p >= p_star(*cat.stake(issue_tier(cat, issue, tags, settled=False))):   # rule 6
        act = dict(act="proceed", issue=issue, side=s_star)
    else:
        act = route("inform", perm if perm != interim else cat.other(issue, perm), s_star, question=a["ustar"] or None)
    if act["act"] == "route" and act["because"] != "flag":                    # rule 7
        hs = {h for s in sides for h in holders_of(sit, g[s]["class"])}
        if hs and hs <= unreachable_holders(cat, sit, tags):
            deleg = any(delegation_active(sit, d, tags) and d.get("to", "agent") == "agent" and
                        set(d.get("holds") or []) & {g[s]["class"] for s in sides} for d in _auth(sit, "delegations"))
            if deleg and s_star is not None and g[s_star]["within"]:
                act = dict(act="proceed", issue=issue, side=s_star, basis="delegated; no human reachable")
            else:
                act = dict(act="proceed", issue=issue, side=cat.issues[issue]["default"], basis="default; no human reachable")
    act["support"], act["status"] = a["label"] or a["status"], a["status"]
    if sit.get("unit") is not None:
        act["units"] = [sit["unit"]]
    return act, a


def _pi_for(pi, issue, unit):
    pi = pi or {}
    return pi.get(f"{issue}[{unit}]") if unit is not None and f"{issue}[{unit}]" in pi else pi.get(issue)


def compose(cat, cards, sit, pi=None, flags=(), contested=(), issues=None):
    """3.5 for every issue in play: actions, the plan (action atoms, interim atoms, contingent atoms,
    residue and duty atoms) and coupling violations. flags: [{issue, equity, direction}]."""
    issues = issues or issues_in_play(cat, cards, sit, pi, flags, contested)
    actions, assessed, plan = {}, {}, []
    u = sit.get("unit")
    for I in issues:
        flagged = any(f.get("issue") == I for f in flags) or I in contested
        act, a = compose_issue(cat, cards, sit, I, _pi_for(pi, I, u), flagged)
        actions[I], assessed[I] = act, a
        plan.append({k: v for k, v in act.items() if k not in ("support", "status", "interim")})
        if act["act"] == "route" and act.get("interim"):
            plan.append(dict({"act": "proceed", "issue": I, "side": act["interim"], "interim": True},
                             **({"units": [u]} if u is not None else {})))
    for I in issues:
        a, act = assessed[I], actions[I]
        held = act["side"] if act["act"] == "proceed" else act.get("interim")
        for d in _auth(sit, "delegations"):                                    # rule 8: contingent atoms
            if d.get("to", "agent") != "agent" or delegation_active(sit, d, a["tags"]):
                continue
            for s in cat.sides(I):
                cls = cat.klass(I, s)
                if cls in (d.get("holds") or []) and not cat.restrictive(cls) and not (act["act"] == "proceed" and act["side"] == s):
                    plan.append({"act": "contingent", "when": list(d.get("when") or []), "then": {"issue": I, "side": s}})
        if held is not None:                                                   # rule 9: residue (H11)
            lose = cat.other(I, held)
            for t in sorted(a["tags"]):
                if t in cat.tag and cat.issue_of(t) == I and cat.side(t) == lose:
                    for e, st in cat.equities(t).items():
                        res = (cat.equity_defs.get(e) or {}).get("residue")
                        atom = {"act": "residue", "issue": I, "equity": e, "atoms": list(res or [])}
                        if st == "strong" and res and atom not in plan:
                            plan.append(atom)
        for d in _auth(sit, "delegations"):                                    # rule 9: duties of a used delegation
            used = d.get("duties") and delegation_active(sit, d, a["tags"]) and (
                (act["act"] == "route" and d.get("to") in act.get("to", [])) or
                (act["act"] == "proceed" and a["gate"][act["side"]]["via"] == "delegation"
                 and act["side"] in cat.sides(I) and cat.klass(I, act["side"]) in (d.get("holds") or [])))
            atom = {"act": "duty", "from": d.get("id"), "atoms": list(d.get("duties") or [])}
            if used and atom not in plan:
                plan.append(atom)
    viol = []
    for rule in cat.coupling:
        (I, s), = rule["if"].items()
        (J, t), = rule["then"].items()
        if actions.get(I, {}).get("act") == "proceed" and actions[I].get("side") == s and \
                not (actions.get(J, {}).get("act") == "proceed" and actions[J].get("side") == t):
            viol.append(rule)
    return {"actions": actions, "plan": plan, "coupling": viol, "assessed": assessed}


def compose_record(cat, rec, cards, pi=None, flags=(), contested=(), authority=None):
    """compose() over a record: issues with a fitting unit-scoped card are composed once per unit (a unit's
    situation = facts about it + facts about no unit); every other issue once over all facts."""
    r = rec.get("record", rec)
    whole = situation_from_record(cat, r)
    sits = {None: whole}
    for u in r.get("units") or []:
        sits[u["id"]] = situation_from_record(cat, r, u["id"])
    if authority is not None:
        for s in sits.values():
            s["authority"] = authority
    per_unit = {c["issue"] for c in cards if c.get("units") and any(_card_fits(c, s) for k, s in sits.items() if k)}
    out = {"actions": {}, "plan": [], "coupling": [], "assessed": {}}
    for u, s in sits.items():
        ip = issues_in_play(cat, cards, s, pi, flags, contested)
        issues = [I for I in ip if (I in per_unit) == (u is not None)]
        if u is not None:
            issues = [I for I in issues if any(c["issue"] == I and c.get("units") and _card_fits(c, s) for c in cards)]
        if not issues:
            continue
        res = compose(cat, cards, s, pi, flags, contested, issues)
        for I, a in res["actions"].items():
            out["actions"][(I, u) if u else I] = a
            out["assessed"][(I, u) if u else I] = res["assessed"][I]
        out["plan"] += [x for x in res["plan"] if x not in out["plan"]]
        out["coupling"] += res["coupling"]
    return out


# ------------------------------------------------------------------------------------------------ 3.6
def action_key(a):
    """A change of the composed action: proceed + side, or route + holders."""
    return (a["act"], a.get("side")) if a["act"] == "proceed" else ("route", tuple(sorted(a.get("to") or [])))


def single_changes(cat, tags, issue=None):
    """Single-tag probes: per factor stem one rung up (its first rung if absent) and one rung down; every
    condition toggled."""
    out, top = [], cat.top(tags)
    for stem, lad in cat.ladder.items():
        if issue and cat.factors[stem]["issue"] != issue:
            continue
        if stem in top:
            i = cat.tag[top[stem]][2]
            out.append("-" + top[stem])
            if i + 1 < len(lad):
                out.append("+" + lad[i + 1])
        else:
            out.append("+" + lad[0])
    return out + [("-" if c in tags else "+") + c for c in cat.conditions]


def flip_set(cat, cards, sit, issue, pi=None):
    base = action_key(compose(cat, cards, sit, pi, issues=[issue])["actions"][issue])
    out = []
    for ch in single_changes(cat, sit["tags"], issue):
        new = compose(cat, cards, dict(sit, tags=apply_change(cat, sit["tags"], [ch])), pi, issues=[issue])["actions"][issue]
        if action_key(new) != base:
            out.append((ch, action_key(new)))
    return out


def watch_for(cat, cards, sit, pi=None):
    """Gold watch_for: flip-set additions of absent tags, ranked by how many issues they move."""
    issues = issues_in_play(cat, cards, sit, pi)
    base = compose(cat, cards, sit, pi, issues=issues)["actions"]
    moved = {}
    for ch in single_changes(cat, sit["tags"]):
        if ch[0] == "+":
            new = compose(cat, cards, dict(sit, tags=apply_change(cat, sit["tags"], [ch])), pi, issues=issues)["actions"]
            m = [I for I in issues if action_key(new[I]) != action_key(base[I])]
            if m:
                moved[ch[1:]] = m
    return sorted(moved.items(), key=lambda kv: (-len(kv[1]), kv[0]))


def lint_horty(cat, cards):
    """Consistency (qiyas naqd / Horty): no two opposite-outcome cards on one issue (and unit) may both force
    on the union of their reasons plus their scopes and required conditions ([v2] near-miss scope)."""
    bad, oc = [], [c for c in cards if c.get("outcome")]
    for i, p in enumerate(oc):
        for q in oc[i + 1:]:
            if p["issue"] != q["issue"] or p["outcome"] == q["outcome"] or (p.get("units") or q.get("units")) and \
                    p.get("units") != q.get("units") and p["id"].split("/")[0] == q["id"].split("/")[0]:
                continue
            if p["requires"] & q["forbids"] or q["requires"] & p["forbids"]:
                continue
            for Rp in p.get("alts") or [p["reason"]]:
                for Rq in q.get("alts") or [q["reason"]]:
                    Y = cat.close(Rp | Rq) | p["requires"] | q["requires"] | p.get("scope", set()) | q.get("scope", set())
                    if p["forbids"] & Y or q["forbids"] & Y:
                        continue
                    vp, vq = compare(cat, p, Y)["verdict"], compare(cat, q, Y)["verdict"]
                    if vp in FORCING and vq in FORCING:
                        bad.append({"p": card_key(p), "q": card_key(q), "verdicts": (vp, vq), "Y": sorted(Y)})
    return bad


def settled_value(cat, cards, Y, issue, s):
    sup = support(cat, cards, Y, issue)
    return 0 if sup["status"] != "settled" else (1 if sup["side"] == s else -1)


def lint_monotone(cat, cards, tags, issue):
    """Adding a factor favoring s never moves the settled outcome away from s; removing one never toward s."""
    viol = []
    for ch in single_changes(cat, tags, issue):
        t = ch[1:]
        if cat.is_cond(t):
            continue
        s = cat.side(t)
        before = settled_value(cat, cards, tags, issue, s)
        after = settled_value(cat, cards, apply_change(cat, tags, [ch]), issue, s)
        if (ch[0] == "+" and after < before) or (ch[0] == "-" and after > before):
            viol.append((ch, before, after))
    return viol


# ------------------------------------------------------------------------------------------------ plan atoms
def _atoms(plan):
    """Expand plan atoms to (key, attributes) pairs, one per unit. Keys identify an atom; attributes are
    compared only where the gold states them (a gold atom without `because` matches any reason)."""
    out = []
    for a in plan:
        units = as_list(a.get("units") or a.get("unit")) or [None]
        for u in units:
            if a["act"] == "proceed":
                out.append((("proceed", a["issue"], a["side"], u, bool(a.get("interim"))), {}))
            elif a["act"] == "route":
                attrs = {k: (frozenset(as_list(a[k])) if k == "to" else a[k]) for k in ("because", "to", "recommend") if k in a}
                out.append((("route", a["issue"], a.get("side"), u), attrs))
            elif a["act"] == "contingent":
                out.append((("contingent", frozenset(a["when"]), a["then"]["issue"], a["then"]["side"]), {}))
            elif a["act"] in ("residue", "duty"):
                ident = a.get("equity") if a["act"] == "residue" else a.get("from")
                out.append(((a["act"], ident), {"atoms": frozenset(a.get("atoms") or [])}))
            else:
                out.append(((a["act"], str(sorted(a.items()))), {}))
    return out


def plan_diff(gold, got):
    """Atom-by-atom comparison: matched, missing (gold only), extra (solver only), attribute mismatches."""
    g, s = dict(_atoms(gold)), dict(_atoms(got))
    matched, attr = [], []
    for k in g:
        if k in s:
            bad = {a: (v, s[k].get(a)) for a, v in g[k].items() if s[k].get(a) != v}
            (attr.append((k, bad)) if bad else matched.append(k))
    return {"matched": matched, "missing": [k for k in g if k not in s], "extra": [k for k in s if k not in g],
            "attr": attr}


def plan_atoms(plan):
    """Exact atom set (keys + attributes), for strict equality checks."""
    return {(k, tuple(sorted((a, v) for a, v in attrs.items()))) for k, attrs in _atoms(plan)}


def plan_matches(gold, got):
    d = plan_diff(gold, got)
    return not d["missing"] and not d["extra"] and not d["attr"]
