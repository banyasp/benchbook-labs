"""Solver v3 for Benchbook v7 (spec: drafts/SPEC-v7-v1.md, section 3). Pure Python + PyYAML.

Per issue I:  3.0 normalize -> 3.1 authority gate -> 3.2 compare each served card -> 3.3 support
-> 3.4 stability over uncertain tags -> 3.5 compose the harness action.  3.6: derived guidance + lints.
Keeps solver_v2's effective() blocking semantics. Every choice the spec leaves open is marked
"CHOICE" in a comment and listed in results/REPORT.md.
"""
import yaml

RHO = 0.25
STRENGTH = {"weak": 1, "strong": 2}
FORCING = ("binding", "analogous")
VERDICT_RANK = {"binding": 3, "analogous": 2, "distinguished": 1, "off_point": 0}
# Spec 3.2 scores a new-against distinction at its catalog strength (its own COMPARE example needs this);
# solver_v2 skipped equities on which the new factor is itself blocked. True = proposed amendment A5.
NEW_AGAINST_EFFECTIVE = False


def p_star(L, k, rho=RHO):
    """The one act-or-route threshold (3.5 and 5; fixes red-team m2): (L - k) / (1 + L - rho)."""
    return (L - k) / (1 + L - rho)


def load_yaml(path):
    with open(path) as fh:
        return yaml.safe_load(fh)


# ------------------------------------------------------------------------------------------------ catalog
class Catalog:
    """A v7 catalog (spec 1) plus derived indices.

    Tags are 'ID' (unscaled factor), 'ID@rung' (scaled factor) or a condition id ('cond.*').
    `flags` switches on factors carrying `flag:` (e.g. the DOHA doctrine extension)."""

    def __init__(self, doc, flags=()):
        c = doc.get("catalog", doc)
        self.raw, self.flags = c, set(flags)
        self.id, self.version = c["id"], str(c.get("version", ""))
        self.issues = c["issues"]
        self.equity_defs = c.get("equities") or {}
        dims = c.get("dimensions") or {}   # name -> [rungs] or {rungs: [...], mirror: bool}
        self.dimensions = {d: (v["rungs"] if isinstance(v, dict) else v) for d, v in dims.items()}
        self.dim_mirror = {d: bool(isinstance(v, dict) and v.get("mirror")) for d, v in dims.items()}
        self.conditions = c.get("conditions") or {}
        self.actions = c.get("actions") or {}
        self.auth = c.get("authority") or {}
        self.stakes = c.get("stakes") or {}
        self.coupling = c.get("coupling") or []
        self.all_factors = c.get("factors") or {}
        self.factors = {k: v for k, v in self.all_factors.items() if not v.get("flag") or v["flag"] in self.flags}
        self.tag = {}      # tag -> (stem, rung or None, closure index)
        self.ladder = {}   # stem -> its tags in closure order (a tag implies every tag before it)
        for fid, f in self.factors.items():
            if "rungs" in f:
                order = self.dimensions[f["dimension"]]
                rungs = sorted(f["rungs"], key=order.index)
                if f.get("mirror_of"):          # CHOICE: a mirror face reads "value <= r", so it closes upward
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

    # --- tag helpers
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
        """equity -> strength for this tag. CHOICE: for a scaled factor a string rung value overrides every
        listed equity's strength; a dict rung value gives per-equity strengths (SEC-F A20d)."""
        f = self.fac(t)
        r = self.tag[t][1]
        if r is None:
            return dict(f["equities"])
        spec = f["rungs"][r]
        return dict(spec) if isinstance(spec, dict) else {e: spec for e in f["equities"]}

    def on_issue(self, tags, issue):
        return {t for t in tags if t in self.tag and self.issue_of(t) == issue}

    def close(self, tags):
        """3.0: drop unknown tags; a rung tag implies every lower rung of the same factor."""
        out = set()
        for t in tags:
            if t in self.conditions:
                out.add(t)
            elif t in self.tag:
                lad = self.ladder[self.stem(t)]
                out.update(lad[: self.tag[t][2] + 1])
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

    # --- issue / action helpers
    def sides(self, issue):
        return list(self.issues[issue]["sides"])

    def other(self, issue, s):
        a, b = self.sides(issue)
        return b if s == a else a

    def klass(self, issue, s):
        return self.issues[issue]["action"][s]

    def restrictive(self, cls):
        return self.actions.get(cls, {}).get("direction") == "restrictive"

    def tier_max(self, tiers):
        tiers = [t for t in tiers if t]
        return max(tiers, key=self.tier_order.index) if tiers else None

    def stake(self, tier):
        s = self.stakes.get(tier or self.tier_order[0]) or {"L": 1, "k": 0.2}
        return s["L"], s["k"]

    def l_max(self):
        return max((v["L"] for v in self.stakes.values()), default=1)


def load_catalog(path, flags=()):
    return Catalog(load_yaml(path), flags)


# ------------------------------------------------------------------------------------------------ records
def situation_from_record(cat, rec, unit=None):
    """The decision-point layer (P1) as solver input: closed tags, uncertain values, agent, authority.

    CHOICE: facts with status `rejected`, `known_at_decision: false` or `use: credibility_only` add no tags;
    a `disputed` fact's tags become uncertain (absent..its rung); `situation.uncertain` adds explicit
    possible-value sets ({stem or condition: [values]}). With `unit`, only facts about that unit or
    about no unit count."""
    r = rec.get("record", rec)
    s = r["situation"]
    tags, unc = set(), {}
    for f in s.get("facts") or []:
        if unit is not None and f.get("about") not in (None, unit):
            continue
        if f.get("status") == "rejected" or f.get("known_at_decision") is False or f.get("use") == "credibility_only":
            continue
        ft = cat.close(f.get("tags") or [])
        if f.get("status") == "disputed":
            for stem, t in cat.top(ft).items():
                lad = cat.ladder[stem]
                unc[stem] = ["absent"] + [x.split("@")[-1] if "@" in x else "present" for x in lad[: cat.tag[t][2] + 1]]
            unc.update({c: ["absent", "present"] for c in ft if cat.is_cond(c)})
        else:
            tags |= ft
    for k, v in (s.get("uncertain") or {}).items():
        unc[k] = list(v)
    return {"tags": tags, "uncertain": unc, "agent": s.get("agent") or {},
            "authority": s.get("authority") or {}, "unit": unit, "record_id": r["id"]}


def cards_from_record(cat, rec, with_flips=True):
    """Exemplar cards from a record: one card per holding (per unit when the record has units), plus
    each guidance.flips entry compiled to a near-miss card (3.6) when the record has no units."""
    r = rec.get("record", rec)
    prov = (r.get("provenance") or {}).get("authority") or {}
    base = {"id": r["id"], "status": prov.get("status", "current"), "rank": prov.get("rank", 0),
            "requires": frozenset(), "forbids": frozenset(), "route": None}
    cards = []
    for h in (r.get("resolution") or {}).get("holdings") or []:
        X = frozenset(situation_from_record(cat, r, h.get("unit"))["tags"])
        cards.append(dict(base, issue=h["issue"], unit=h.get("unit"), outcome=h["outcome"],
                          reason=frozenset(cat.close(h["reason"])), X=X, force=h.get("force", "required"),
                          kind="holding"))
    if with_flips and not r.get("units"):
        X = frozenset(situation_from_record(cat, r)["tags"])
        for fl in (r.get("guidance") or {}).get("flips") or []:
            cards.append(compile_flip(cat, base, X, fl))
    return cards


def apply_change(cat, tags, change):
    """X (+) change. '+T' adds T with closure; '-T' removes T and every higher rung of T's factor."""
    out = set(tags)
    for ch in change:
        sign, t = ch[0], ch[1:]
        if sign == "+":
            out |= cat.close([t])
        elif t in cat.tag:
            lad = cat.ladder[cat.stem(t)]
            out -= set(lad[cat.tag[t][2]:])
        else:
            out.discard(t)
    return out


def compile_flip(cat, base, X, fl):
    """3.6: a typed flip -> a synthetic near-miss card. X' = X (+) change; reason as stated, else every X'
    factor on the issue favoring the new outcome. CHOICE: conditions the change adds (removes) become
    `requires` (`forbids`) -- the card is inapplicable unless they hold; a `route` flip compiles to a route
    card that applies when its added factor tags are present and its removed ones absent."""
    th = fl["then"]
    I = th["issue"]
    Xp = frozenset(apply_change(cat, X, fl["change"]))
    adds = {c[1:] for c in fl["change"] if c[0] == "+"}
    rems = {c[1:] for c in fl["change"] if c[0] == "-"}
    card = dict(base, id=f"{base['id']}/{fl['id']}", issue=I, unit=None, X=Xp, kind="flip",
                force=th.get("force", "required"),
                requires=frozenset(c for c in adds if cat.is_cond(c)),
                forbids=frozenset(c for c in rems if cat.is_cond(c)))
    if "route" in th:
        card.update(outcome=None, route=th["route"], reason=frozenset(),
                    trig_add=frozenset(cat.close(t for t in adds if not cat.is_cond(t))),
                    trig_rem=frozenset(t for t in rems if not cat.is_cond(t)))
    else:
        o = th["outcome"]
        R = fl.get("reason") or [t for t in cat.on_issue(Xp, I) if cat.side(t) == o]
        card.update(outcome=o, reason=frozenset(cat.close(R)))
    return card


# ------------------------------------------------------------------------------------------------ 3.1 gate
def _delegations(sit):
    return [d for d in (sit["authority"].get("delegations") or []) if d.get("to", "agent") == "agent"]


def delegation_active(sit, d, tags):
    """3.1: active iff every `when` condition is present (uncertain conditions are absent in some
    completion, so they never activate a delegation)."""
    return all(c in tags and c not in sit.get("uncertain", {}) for c in d.get("when") or [])


def required_tier(cat, issue, s, tags):
    """3.1: the max of the class tier and every present tag's tier floor on this issue (permissive only).
    A restrictive class needs no level; its declared tier (if any) is kept for stakes only."""
    cls = cat.klass(issue, s)
    t = cat.actions.get(cls, {}).get("tier")
    if cat.restrictive(cls):
        return None, t
    floors = [v for k, v in (cat.auth.get("tier_floors") or {}).items() if k in tags and cat.issue_of(k) == issue]
    t = cat.tier_max([t] + floors) or cat.tier_order[0]   # CHOICE: an untiered permissive class is T0
    return t, t


def issue_tier(cat, issue, tags):
    """CHOICE (amends 3.5 'required tier of s*'): the stakes tier of an issue is the max over its sides,
    so the p* gate does not depend on which side the model picks."""
    return cat.tier_max([required_tier(cat, issue, s, tags)[1] for s in cat.sides(issue)]) or cat.tier_order[0]


def holder(cat, sit, cls):
    for d in sit["authority"].get("deciders") or []:
        if cls in (d.get("holds") or []):
            return d["holder"]
    return sit["agent"].get("serves")


def gate(cat, sit, issue, tags):
    """3.1 per issue: side -> {within, class, holder, tier}. `tags` are the completion being gated.
    CHOICE: a role whose level is null (none, recommend) cannot act at all, so 'restrictive actions are
    always within any role that can act at all' applies only to roles with a level."""
    roles = cat.auth.get("roles") or {}
    lvl = roles.get(sit["agent"].get("role", "none"))
    out = {}
    for s in cat.sides(issue):
        cls = cat.klass(issue, s)
        need, _ = required_tier(cat, issue, s, tags)
        deleg = any(cls in (d.get("holds") or []) and delegation_active(sit, d, tags) for d in _delegations(sit))
        by_level = (lvl is not None and need is not None and
                    cat.levels.index(lvl) >= cat.levels.index(cat.tiers[need]))
        within = ((cat.restrictive(cls) and lvl is not None) or cls in (cat.auth.get("inherent") or [])
                  or deleg or by_level) and cls not in (cat.auth.get("non_delegable_to_agent") or [])
        out[s] = {"within": within, "class": cls, "holder": holder(cat, sit, cls), "tier": need}
    return out


def gate_result(cat, sit, issue, tags):
    """The WHO-block summary scored by r_who: ('within', None) if every side is within role, else
    ('route', holder of the first out-of-role class)."""
    g = gate(cat, sit, issue, tags)
    out = [s for s in cat.sides(issue) if not g[s]["within"]]
    return ("within", None) if not out else ("route", g[out[0]]["holder"])


def order_effects(cat, sit, issue, tags):
    """3.1 orders (optional in v7.0). Returns (tags to exclude on `issue`, flag raised?).
    CHOICE: literal reading -- an active order excludes every situation factor on the issue (either side)
    whose equities all fall in `excludes`."""
    excl, flag = set(), False
    for od in sit["authority"].get("orders") or []:
        if od["directs"]["issue"] != issue:
            continue
        if not all(c in tags for c in od.get("active_when") or []):
            continue
        if any(c in tags for c in od.get("disabled_by") or []):
            flag = True
            continue
        ex = set(od.get("excludes") or [])
        excl |= {t for t in cat.on_issue(tags, issue) if set(cat.equities(t)) <= ex}
    return excl, flag


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
    blocked = any(g in cat.tag and cat.issue_of(g) == I and cat.side(g) != s and cat.equities(g).get(e) == "strong"
                  for g in facts)
    return 0 if blocked else 1


def mirror_set(cat, R, o):
    """Horty 2021 Def. 9 in factor form: for a scaled reason F@r favoring o, the o-bar face G (mirror_of)
    tags entailed by 'value <= r' -- only for dimensions marked `mirror: true` (off by default)."""
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
            pair = g.get("mirror_of") == cat.stem(t) or f.get("mirror_of") == gid
            if pair and g.get("favors") != o and g.get("dimension") == dim:
                out |= {f"{gid}@{x}" for x in g["rungs"] if order.index(x) >= order.index(r)}
    return out


def _covered(cat, d, pool, facts, e, need):
    """Is equity e of distinction d covered by a factor in `pool` (not d's stem) with effective strength
    (computed within `facts`) >= need?"""
    return any(cat.stem(g) != cat.stem(d) and effective(cat, g, facts, e) >= need for g in pool)


def compare(cat, card, Y):
    """3.2: one card against situation tags Y (any issues; restricted here to the card's issue).
    Returns {verdict, missing, new, significant, uncovered}."""
    I, o = card["issue"], card["outcome"]
    ob = cat.other(I, o)
    conds = {t for t in Y if cat.is_cond(t)}
    if not card["requires"] <= conds or card["forbids"] & conds:
        return {"verdict": "off_point", "missing": [], "new": [], "significant": [], "uncovered": {},
                "note": "conditions unmet"}
    Y, X = cat.on_issue(Y, I), cat.on_issue(card["X"], I)
    R = cat.on_issue(card["reason"], I)
    Yo = {t for t in Y if cat.side(t) == o}
    Xob = {t for t in X if cat.side(t) == ob}
    mir = mirror_set(cat, R, o)
    # distinctions, collapsed per stem (fixes RT-7a / m7)
    missing = sorted(t for s, t in cat.top(R).items() if t not in Y)
    cand = {t for t in Y if cat.side(t) == ob and t not in Xob and t not in mir}
    new = sorted(cat.top(cand).values())
    # per-equity significance (fixes M2 / RT-4 / RT-5)
    unc = {}
    for d in missing:
        unc[d] = [e for e, st in cat.equities(d).items() if not _covered(cat, d, Yo, Y, e, STRENGTH[st])]
    for d in new:
        need = {e: (effective(cat, d, Y, e) if NEW_AGAINST_EFFECTIVE else STRENGTH[st]) for e, st in cat.equities(d).items()}
        unc[d] = [e for e in need if need[e] and not _covered(cat, d, Xob, X, e, need[e])]
    sig = sorted(d for d in missing + new if unc[d] or cat.knockout(d))
    # off point (fixes M4): no reason factor present (stem level) and no reason equity covered
    rstems = {cat.stem(t) for t in R}
    present = any(cat.stem(t) in rstems for t in Y)
    any_cov = any(_covered(cat, t, Yo, Y, e, STRENGTH[st]) for t in cat.top(R).values()
                  for e, st in cat.equities(t).items())
    if not present and not any_cov:
        return {"verdict": "off_point", "missing": [], "new": [], "significant": [], "uncovered": {}}
    if not missing and not new:
        v = "binding"
    else:
        v = "distinguished" if sig else "analogous"
    return {"verdict": v, "missing": missing, "new": new, "significant": sig, "uncovered": unc}


def route_applies(cat, card, Y):
    conds = {t for t in Y if cat.is_cond(t)}
    return (card["requires"] <= conds and not card["forbids"] & conds
            and card["trig_add"] <= set(Y) and not card["trig_rem"] & set(Y))


# ------------------------------------------------------------------------------------------------ 3.3
def card_key(c):
    return (c["id"], c["issue"], c.get("unit"))


def support(cat, cards, Y, issue, unit=None, record_id=None):
    """3.3 over the served cards only. Returns {status: settled|bounded|open|unprecedented, side, label,
    route (a route card that applies), permissible, verdicts}. A unit card of the situation's own record
    counts only for that unit (units are record-local)."""
    live = [c for c in cards if c["issue"] == issue
            and not (c.get("unit") and c["id"].split("/")[0] == record_id and c["unit"] != unit)
            and c.get("status", "current") == "current" and c.get("force", "required") in ("required", "permitted")]
    verdicts, route, forcing, permissible, on_point = {}, None, {}, set(), set()
    for c in live:
        if c.get("route"):
            ok = route_applies(cat, c, Y)
            verdicts[card_key(c)] = {"verdict": "applies" if ok else "off_point", "route": c["route"]}
            route = route or (c["route"] if ok else None)
            continue
        r = compare(cat, c, Y)
        verdicts[card_key(c)] = r
        v, o = r["verdict"], c["outcome"]
        if v in FORCING and c.get("force", "required") == "required":
            best = forcing.get(o)
            cand = (c.get("rank", 0), VERDICT_RANK[v])
            forcing[o] = max(best, cand) if best else cand
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
        label = "binding" if vr == VERDICT_RANK["binding"] else "analogous"
        return dict(res, status="settled", side=s, label=label, permissible=permissible | {s})
    status = {2: "bounded", 1: "open", 0: "unprecedented"}[len(on_point)]
    return dict(res, status=status)


# ------------------------------------------------------------------------------------------------ 3.4
def _value_tags(cat, u, v):
    if v in (None, "absent"):
        return set()
    if cat.is_cond(u) or v == "present":
        return {u} if cat.is_cond(u) else {cat.ladder[u][0]}
    return cat.close([f"{u}@{v}"])


def _vkey(cat, u, v):
    """Order possible values: absent < present / lower rung < higher rung (closure order)."""
    if v in (None, "absent"):
        return -1
    if v == "present" or cat.is_cond(u):
        return 0
    return cat.tag[f"{u}@{v}"][2]


def _relevant(cat, sit, issue):
    return {u: vs for u, vs in sit["uncertain"].items()
            if cat.is_cond(u) or (u in cat.factors and cat.factors[u]["issue"] == issue)}


def completion(cat, sit, issue, side, fixed=None):
    """3.4: the most-`side` completion of `issue` (Odekerken, Bex & Prakken 2023). Uncertain factor stems
    favoring `side` take their highest possible value, the others their lowest. CHOICE: an uncertain
    condition is present iff it appears in the `when` of a delegation covering side's action class."""
    fixed = fixed or {}
    unc = _relevant(cat, sit, issue)
    tags = set(sit["tags"])
    for u in unc:
        tags -= set(cat.ladder.get(u, [u]))
    helps = {c for d in _delegations(sit) if cat.klass(issue, side) in (d.get("holds") or [])
             for c in d.get("when") or []}
    for u, vals in unc.items():
        if u in fixed:
            v = fixed[u]
        elif cat.is_cond(u):
            v = "present" if (u in helps and "present" in vals) else min(vals, key=lambda x: _vkey(cat, u, x))
        else:
            hi = cat.factors[u]["favors"] == side
            v = (max if hi else min)(vals, key=lambda x: _vkey(cat, u, x))
        tags |= _value_tags(cat, u, v)
    return tags


def _run(cat, cards, sit, issue, tags):
    s0 = dict(sit, tags=tags, uncertain={})
    excl, oflag = order_effects(cat, s0, issue, tags)
    sup = support(cat, cards, set(tags) - excl, issue, sit.get("unit"), sit.get("record_id"))
    return dict(sup, gate=gate(cat, s0, issue, tags), flag=oflag, tags=tags)


def _stable(cat, a, b, issue):
    return (a["status"] == b["status"] == "settled" and a["side"] == b["side"] and a["route"] == b["route"]
            and all(a["gate"][s]["within"] == b["gate"][s]["within"] for s in cat.sides(issue)))


def assess(cat, cards, sit, issue, fixed=None):
    """3.3 + 3.4 for one issue: support on each extreme completion; stable iff both settle the same side
    with the same gate. Unstable -> status 'unstable', U* = uncertain items whose resolution alone (to
    either of its extreme values) makes the issue stable; the gate is the conservative AND of both."""
    unc = {u: v for u, v in _relevant(cat, sit, issue).items() if u not in (fixed or {})}
    if not unc:
        return dict(_run(cat, cards, sit, issue, completion(cat, sit, issue, cat.sides(issue)[0], fixed)),
                    stable=True, ustar=[])
    ext = [_run(cat, cards, sit, issue, completion(cat, sit, issue, s, fixed)) for s in cat.sides(issue)]
    if _stable(cat, ext[0], ext[1], issue):
        return dict(ext[0], stable=True, ustar=[])
    ustar = []
    if fixed is None:
        for u, vals in unc.items():
            lo, hi = (f(vals, key=lambda x: _vkey(cat, u, x)) for f in (min, max))
            if all(assess(cat, cards, sit, issue, {u: v})["stable"] for v in (lo, hi)):
                ustar.append(u)
    g = {s: dict(ext[0]["gate"][s], within=ext[0]["gate"][s]["within"] and ext[1]["gate"][s]["within"])
         for s in cat.sides(issue)}
    return dict(ext[0], status="unstable", side=None, label=None, gate=g, stable=False, ustar=sorted(ustar),
                flag=ext[0]["flag"] or ext[1]["flag"], route=ext[0]["route"] or ext[1]["route"])


# ------------------------------------------------------------------------------------------------ 3.5
def issues_in_play(cat, cards, sit, pi=None, flags=(), contested=()):
    """CHOICE: 3.5 composes 'per issue'; the issues in play are those with a situation tag (certain or
    uncertain), a served card, a distribution, a flag or a contested label."""
    out = {cat.issue_of(t) for t in sit["tags"] if t in cat.tag}
    out |= {cat.factors[u]["issue"] for u in sit["uncertain"] if u in cat.factors}
    out |= {c["issue"] for c in cards} | set(pi or {}) | {f["issue"] for f in flags} | set(contested)
    return [I for I in cat.issues if I in out]


def unreachable(cat, sit, issue, tags):
    """3.5: no human is reachable iff every holder of the issue's classes has a present, certain
    `cond.*` whose catalog entry names it as `unreachable`."""
    hs = {holder(cat, sit, cat.klass(issue, s)) for s in cat.sides(issue)} - {None}
    down = {cat.conditions[c].get("unreachable") for c in tags if cat.is_cond(c) and c not in sit["uncertain"]}
    return bool(hs) and hs <= down


def _argmax(dist):
    if not dist:
        return None, None
    s = max(sorted(dist), key=lambda k: dist[k])
    return s, dist[s]


def compose_issue(cat, cards, sit, issue, pi=None, flagged=False):
    """3.5 for one issue -> (action, assessment). pi: {side: p} or None."""
    a = assess(cat, cards, sit, issue)
    g, sides, tags = a["gate"], cat.sides(issue), a["tags"]
    out_role = [s for s in sides if not g[s]["within"]]
    s_star, p = _argmax(pi)
    decider = g[out_role[0]]["holder"] if out_role else g[sides[0]]["holder"]
    if not out_role:
        decider = next((g[s]["holder"] for s in sides if not cat.restrictive(g[s]["class"])), decider)

    def route(because, rec, to=None, **kw):
        return dict(act="route", issue=issue, to=to or decider, because=because, recommend=rec, **kw)

    if flagged or a["flag"]:
        act = route("flag", s_star, to=sit["agent"].get("serves") or decider)
    elif a["route"]:
        act = route(a["route"], a["side"] or s_star)
    elif a["status"] == "settled":
        s = a["side"]
        act = dict(act="proceed", issue=issue, side=s) if g[s]["within"] else route("authorize", s, g[s]["holder"])
    elif out_role:   # CHOICE: an unsettled issue with an out-of-role side goes to that side's holder
        act = route("authorize", s_star, g[out_role[0]]["holder"])
    elif s_star is not None and p >= p_star(*cat.stake(issue_tier(cat, issue, tags))):
        act = dict(act="proceed", issue=issue, side=s_star)
    else:
        act = route("inform", s_star, question=a["ustar"] or None)
    if act["act"] == "route" and unreachable(cat, sit, issue, tags):
        deleg = any(delegation_active(sit, d, tags) and set(d.get("holds") or []) & {cat.klass(issue, s) for s in sides}
                    for d in _delegations(sit))
        if deleg and s_star is not None and g[s_star]["within"]:   # CHOICE: the delegate decides on its own s*
            act = dict(act="proceed", issue=issue, side=s_star, basis="delegated; no human reachable")
        else:
            act = dict(act="proceed", issue=issue, side=cat.issues[issue]["default"], basis="default; no human reachable")
    act["support"], act["status"] = a["label"] or a["status"], a["status"]
    if sit.get("unit") is not None:
        act["unit"] = sit["unit"]
    return act, a


def compose(cat, cards, sit, pi=None, flags=(), contested=(), issues=None):
    """3.5: the harness action for every issue in play, the plan (actions + contingent atoms from
    delegations whose conditions are absent) and coupling violations. flags: [{issue, equity, direction}]."""
    pi = pi or {}
    issues = issues or issues_in_play(cat, cards, sit, pi, flags, contested)
    actions, assessed, plan = {}, {}, []
    for I in issues:
        flagged = any(f.get("issue") == I for f in flags) or I in contested
        actions[I], assessed[I] = compose_issue(cat, cards, sit, I, pi.get(I), flagged)
        plan.append({k: v for k, v in actions[I].items() if k not in ("support", "status")})
    for I in issues:          # contingent atoms (CHOICE: not when the issue is settled on the other side)
        a, act = assessed[I], actions[I]
        for d in _delegations(sit):
            if delegation_active(sit, d, a["tags"]):
                continue
            for s in cat.sides(I):
                if cat.klass(I, s) in (d.get("holds") or []) and not (act["act"] == "proceed" and act["side"] == s) \
                        and not (a["status"] == "settled" and a["side"] != s):
                    plan.append({"act": "contingent", "when": list(d.get("when") or []), "then": {"issue": I, "side": s}})
    viol = []
    for rule in cat.coupling:
        (I, s), = rule["if"].items()
        (J, t), = rule["then"].items()
        if actions.get(I, {}).get("side") == s and actions[I]["act"] == "proceed" and \
                not (actions.get(J, {}).get("act") == "proceed" and actions[J].get("side") == t):
            viol.append(rule)
    return {"actions": actions, "plan": plan, "coupling": viol, "assessed": assessed}


def compose_record(cat, rec, cards, pi=None, flags=(), contested=(), authority=None):
    """compose() over a record's situation, once per unit when the record lists units."""
    r = rec.get("record", rec)
    units = [u["id"] for u in r.get("units") or []] or [None]
    out = {"actions": {}, "plan": [], "coupling": []}
    for u in units:
        sit = situation_from_record(cat, r, u)
        if authority is not None:
            sit["authority"] = authority
        res = compose(cat, cards, sit, pi, flags, contested)
        for I, a in res["actions"].items():
            out["actions"][(I, u) if u else I] = a
        out["plan"] += res["plan"]
        out["coupling"] += res["coupling"]
    return out


# ------------------------------------------------------------------------------------------------ 3.6
def action_key(a):
    """What counts as a change of the composed action: proceed + side, or route + holder."""
    return (a["act"], a.get("side")) if a["act"] == "proceed" else ("route", a.get("to"))


def single_changes(cat, tags, issue=None):
    """Single-tag probes: per factor stem one rung up (its first rung if absent) and one rung down
    (the observed rung removed); every condition toggled."""
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
    """3.6: single-tag additions/removals that change the issue's composed action."""
    base = action_key(compose(cat, cards, sit, pi, issues=[issue])["actions"][issue])
    out = []
    for ch in single_changes(cat, sit["tags"], issue):
        s2 = dict(sit, tags=apply_change(cat, sit["tags"], [ch]))
        new = compose(cat, cards, s2, pi, issues=[issue])["actions"][issue]
        if action_key(new) != base:
            out.append((ch, action_key(new)))
    return out


def watch_for(cat, cards, sit, pi=None):
    """Gold watch_for: flip-set additions of absent tags, ranked by how many issues they move."""
    issues = issues_in_play(cat, cards, sit, pi)
    base = compose(cat, cards, sit, pi, issues=issues)["actions"]
    moved = {}
    for ch in single_changes(cat, sit["tags"]):
        if ch[0] != "+":
            continue
        new = compose(cat, cards, dict(sit, tags=apply_change(cat, sit["tags"], [ch])), pi, issues=issues)["actions"]
        m = [I for I in issues if action_key(new[I]) != action_key(base[I])]
        if m:
            moved[ch[1:]] = m
    return sorted(moved.items(), key=lambda kv: (-len(kv[1]), kv[0]))


def lint_horty(cat, cards):
    """3.6 consistency (qiyas naqd / Horty): no two opposite-outcome cards on one issue may both force
    (binding or analogous) on the union of their reasons (plus the conditions they require)."""
    bad, oc = [], [c for c in cards if c.get("outcome")]
    for i, p in enumerate(oc):
        for q in oc[i + 1:]:
            if p["issue"] != q["issue"] or p["outcome"] == q["outcome"] or p.get("unit") != q.get("unit") and \
                    p["id"].split("/")[0] == q["id"].split("/")[0]:
                continue
            if p["requires"] & q["forbids"] or q["requires"] & p["forbids"]:
                continue
            Y = cat.close(p["reason"] | q["reason"]) | p["requires"] | q["requires"]
            vp, vq = compare(cat, p, Y)["verdict"], compare(cat, q, Y)["verdict"]
            if vp in FORCING and vq in FORCING:
                bad.append({"p": card_key(p), "q": card_key(q), "verdicts": (vp, vq), "Y": sorted(Y)})
    return bad


def settled_value(cat, cards, Y, issue, s):
    """+1 settled on s, 0 unsettled, -1 settled on the other side."""
    sup = support(cat, cards, Y, issue)
    return 0 if sup["status"] != "settled" else (1 if sup["side"] == s else -1)


def lint_monotone(cat, cards, tags, issue):
    """3.6 monotonicity (ArgLLM contestability): around `tags`, adding a factor favoring s never moves the
    settled outcome away from s; removing one never moves it toward s. Returns violations."""
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


def plan_atoms(plan):
    """Normalize plan atoms for atom-by-atom comparison (3.5 / 4 PLAN)."""
    out = set()
    for a in plan:
        u = a.get("unit")
        if a["act"] == "proceed":
            out.add(("proceed", a["issue"], a["side"], u))
        elif a["act"] == "route":
            out.add(("route", a["issue"], a.get("to"), a.get("recommend"), u))
        elif a["act"] == "contingent":
            out.add(("contingent", frozenset(a["when"]), a["then"]["issue"], a["then"]["side"]))
    return out
