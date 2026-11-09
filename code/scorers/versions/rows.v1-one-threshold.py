"""One scorer per row of the PDF's scoring table (v0.4 pp. 23-24), plus the additions DECISIONS 2026-10-25 asks for.

Each scorer takes a ScoringContext (the parsed reply, the answer key, the served case(s), the judge; alignments are
computed once, lazily) and returns its own value -- no weights across rows, no combination, no gate penalty (the
reward is Peter's, TBD). `None` = not scored: the gold for the row is absent, or the row comes after the agent's
`not_governed` (applicability `governs: false` or verdict `relation: not_governed`; Peter: nothing after a decline
is rewarded or punished). A row whose gold is present but whose agent output is missing or malformed scores its
minimum (0, or the ENUM/SET minimum), never None.

Scorers read the raw YAML (`parsed.steps`), not the strict models, so a reply that fails the schema in one field
still gets credit elsewhere; `schema_valid` reports the strict 0/1 separately.

Id namespaces (bench.schema.common): the agent writes live ids of its own choosing (LIVE-F1...) and served case ids
(REF1-F1...); the key holds gold live ids and *global* case ids (DR-...@v1/F1). Live ids are translated through the
judge alignments (never by id coincidence: the agent's LIVE-O2 need not be the gold's LIVE-O2); served ids through
ServedCase.table.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

from bench.schema import AnswerKey, ParsedReply, ServedCase

from . import alignment as A
from .judge import Judge, instruction, noul_question

UNALIGNED = "unaligned:"
UNTRANSLATED = "untranslated:"


# ---------------------------------------------------------------- tolerant readers of the raw reply
def _s(x) -> str:
    return "" if x is None else str(x).strip()


def _as_list(x) -> list:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, (str, int, float)):
        return [x]
    if isinstance(x, dict):
        return [x]
    return list(x)


def _bool(x) -> bool | None:
    if isinstance(x, bool):
        return x
    s = _s(x).lower()
    return True if s in ("true", "yes", "y") else False if s in ("false", "no", "n") else None


def _ids(x) -> list[str]:
    """A list of ids, from a list, a single id, or a comma-separated string."""
    out = []
    for v in _as_list(x):
        if isinstance(v, dict):
            v = v.get("id") or v.get("live") or v.get("case")
        if v is None:
            continue
        out += [p.strip() for p in str(v).split(",") if p.strip()]
    return out


@dataclass
class ScoringContext:
    parsed: ParsedReply
    key: AnswerKey
    served: list[ServedCase] = field(default_factory=list)
    judge: Judge | None = None
    threshold: float = A.THRESHOLD
    notes: dict[str, Any] = field(default_factory=dict)     # per-row diagnostics (paths taken, alignments...)

    # -- raw steps
    def step(self, kind) -> dict:
        d = self.parsed.steps.get(kind)
        return d if isinstance(d, dict) else {}

    @cached_property
    def table(self) -> dict[str, str]:
        t = {}
        for s in self.served:
            t.update(s.table)
        return t

    def to_global(self, served_id) -> str:
        sid = _s(served_id)
        return self.table.get(sid) or (UNTRANSLATED + sid)

    @cached_property
    def served_would_change(self) -> dict[str, str]:
        """served would_change id -> served `then` option id, over every served case."""
        out = {}
        for s in self.served:
            fc = (s.doc.get("case") or {}).get("flip_conditions") or {}
            for w in fc.get("would_change") or []:
                out[w["id"]] = w["then"]
        return out

    # -- governance
    @cached_property
    def agent_not_governed(self) -> bool:
        gov = _bool(self.step("applicability").get("governs"))
        rel = _s(self.step("verdict").get("relation")).lower()
        return gov is False or rel == "not_governed"

    # -- agent items
    @cached_property
    def agent_facts(self) -> dict[str, str]:
        return _items(self.step("fact_enumeration").get("facts"), "fact", "gen-F")

    @cached_property
    def agent_options(self) -> dict[str, str]:
        opts = self.step("fact_enumeration").get("options")
        if isinstance(opts, dict):
            return {str(k): _s(v.get("do") if isinstance(v, dict) else v) for k, v in opts.items()}
        return _items(opts, "do", "gen-O")

    @cached_property
    def agent_considerations(self) -> list[dict]:
        cs = self.step("consideration_enumeration").get("considerations")
        out = []
        for n, c in enumerate(_as_list(cs)):
            if isinstance(c, dict):
                out.append({**c, "id": _s(c.get("id")) or f"gen-C{n + 1}"})
            else:
                out.append({"id": f"gen-C{n + 1}", "why": _s(c)})
        return out

    # -- gold items
    @cached_property
    def gold_options(self) -> dict[str, str]:
        return {k: v.do for k, v in self.key.options.items()}

    @cached_property
    def gold_facts(self) -> dict[str, str] | None:
        return None if self.key.facts is None else {f.id: f.fact for f in self.key.facts}

    # -- alignments (judge calls happen here, once each)
    @cached_property
    def fact_al(self) -> A.Alignment | None:
        if self.gold_facts is None:
            return None
        return A.align(self.agent_facts, self.gold_facts, self.judge, self.threshold, instruction("fact"))

    @cached_property
    def option_al(self) -> A.Alignment:
        return A.align(self.agent_options, self.gold_options, self.judge, self.threshold, instruction("option"))

    @cached_property
    def cons_al(self) -> A.Alignment | None:
        if self.key.considerations is None:
            return None
        gf = self.gold_facts or {}
        gold = {c.id: consideration_text(c.equity, c.why, [gf.get(f, f) for f in c.facts])
                for c in self.key.considerations}
        gen = {c["id"]: consideration_text(c.get("equity"), c.get("why"),
                                           [self.agent_facts.get(f, f) for f in _ids(c.get("facts"))])
               for c in self.agent_considerations}
        return A.align(gen, gold, self.judge, self.threshold, instruction("consideration"))

    def fact_tr(self, agent_id) -> str:
        al = self.fact_al
        return (al.translation.get(_s(agent_id)) if al else None) or UNALIGNED + _s(agent_id)

    def opt_tr(self, agent_id) -> str:
        return self.option_al.translation.get(_s(agent_id)) or UNALIGNED + _s(agent_id)

    def cons_tr(self, agent_id) -> str:
        al = self.cons_al
        return (al.translation.get(_s(agent_id)) if al else None) or UNALIGNED + _s(agent_id)


def _items(xs, text_key: str, prefix: str) -> dict[str, str]:
    """[{id, <text_key>}] or [str] -> {id: text}; invents ids for id-less items, de-duplicates repeated ids."""
    out: dict[str, str] = {}
    for n, x in enumerate(_as_list(xs)):
        if isinstance(x, dict):
            i = _s(x.get("id")) or f"{prefix}{n + 1}"
            t = x.get(text_key) or x.get("text") or x.get("fact") or x.get("do") or ""
        else:
            i, t = f"{prefix}{n + 1}", x
        while i in out:
            i += "'"
        out[i] = _s(t)
    return out


def consideration_text(equity, why, fact_texts) -> str:
    """What a consideration is *about*, for alignment: its equity, its reason, the facts it rests on. Favors and
    weight are left out on purpose: they are scored per pair afterwards, so they must not steer the alignment."""
    t = f"[{_s(equity)}] {_s(why)}".strip()
    facts = [f for f in fact_texts if f]
    return t + (f" (rests on: {'; '.join(facts)})" if facts else "")


# ================================================================= rows
# ---- Overall schema
def schema_valid(ctx: ScoringContext) -> int:
    """SCHEMA_VALIDATOR: 1 iff every required step is present and validates strictly with no repairs."""
    return int(ctx.parsed.strict_ok)


def format_report(parsed: ParsedReply) -> dict:
    """Which steps are present / missing / malformed / repaired, and where each was found (content | think)."""
    present = [k for k in parsed.required() if k in parsed.steps]
    return {
        "present": present,
        "missing": parsed.missing,
        "malformed": {k: parsed.errors[k] for k in present if k not in parsed.models},
        "repaired": {k: v for k, v in parsed.repairs.items() if v},
        "where": dict(parsed.where),
        "in_order": parsed.in_order,
        "unknown_kinds": list(parsed.unknown_kinds),
        "unparsed_chunks": len(parsed.unparsed),
        "duplicate_steps": sorted({d.kind for d in parsed.all_docs
                                   if sum(e.kind == d.kind for e in parsed.all_docs) > 1}),
        "strict_ok": parsed.strict_ok,
    }


# ---- Facts enumeration
def facts_enumeration(ctx: ScoringContext, **w) -> A.EnumScore | None:
    """ENUM_GRADER over the fact alignment. Gold weights from GoldFact.weight."""
    if ctx.fact_al is None:
        return None
    return A.enum_grade(ctx.fact_al, {f.id: f.weight for f in ctx.key.facts}, **w)


# ---- Frame articulation x3 (Jev_Noul)
FRAME_FIELDS = {"question": ("question", "frame_question"), "decider": ("decider", "frame_decider"),
                "role": ("my_role", "frame_role")}


def frame_articulation(ctx: ScoringContext, which: str) -> float | None:
    """Jev_Noul(key.frame.<which>, agent fact_enumeration.frame.<which>) in [0, 1]."""
    if ctx.key.frame is None:
        return None
    fld, q = FRAME_FIELDS[which]
    frame = ctx.step("fact_enumeration").get("frame")
    frame = frame if isinstance(frame, dict) else {}
    cand = _s(frame.get(fld) or (frame.get("role") if fld == "my_role" else None))
    if not cand:
        return 0.0
    return float(ctx.judge.noul(getattr(ctx.key.frame, fld), cand, noul_question(q)))


# ---- Options enumeration + omissions
def options_enumeration(ctx: ScoringContext, **w) -> A.EnumScore:
    """ENUM_GRADER over the judge alignment of the agent's options to the gold option set."""
    return A.enum_grade(ctx.option_al, **w)


def options_omitted(ctx: ScoringContext) -> dict[str, int]:
    """Gold options the agent never enumerated (absent from the alignment), and whether every correct option
    (choice + acceptable) is among them -- then the agent could not have chosen right (the smoke reply did this)."""
    absent = set(ctx.option_al.absent)
    correct = {ctx.key.choice, *ctx.key.acceptable}
    return {"options_omitted": len(absent), "options_correct_omitted": int(correct <= absent)}


# ---- Frame mapping x3 (exact)
def frame_mapping(ctx: ScoringContext, which: str) -> int | None:
    """exact_match(key.frame_map.<which>, agent fact_mapping.frame.<which>) -> 0/1."""
    if ctx.key.frame_map is None or not ctx.served:
        return None
    frame = ctx.step("fact_mapping").get("frame")
    frame = frame if isinstance(frame, dict) else {}
    got = _s(frame.get(which) or (frame.get("my_role") if which == "role" else None)).lower()
    return int(got == getattr(ctx.key.frame_map, which))


# ---- Options map (fact_mapping.options) -- an addition: the PDF lists it inside the fact mapping block
def options_mapping(ctx: ScoringContext) -> dict | None:
    """Agent's live->case option map, translated (agent option -> gold option by alignment; served -> global), vs
    key.option_map. -> {score: correct/|gold map|, correct, n}. A gold option the agent did not enumerate is wrong."""
    gold = ctx.key.option_map
    if gold is None or not ctx.served:
        return None
    amap = ctx.step("fact_mapping").get("options")
    amap = amap if isinstance(amap, dict) else {}
    got = {}
    for a, c in amap.items():
        g = ctx.option_al.translation.get(_s(a))
        if g and g not in got:
            got[g] = None if c in (None, "", "null", "none") else ctx.to_global(c)
    correct = sum(1 for g, c in gold.items() if g in got and got[g] == c)
    return {"score": correct / len(gold) if gold else 1.0, "correct": correct, "n": len(gold)}


# ---- Facts mapping / considerations mapping (translate -> SET_COMPARE per bucket)
BUCKETS = ("matched", "corresponding", "live_only", "case_only")


def _translate_mapping(ctx: ScoringContext, step: dict, live_tr) -> dict[str, set]:
    out = {}
    for b in ("matched", "corresponding"):
        pairs = set()
        for p in _as_list(step.get(b)):
            if isinstance(p, dict):
                pairs.add((live_tr(p.get("live")), ctx.to_global(p.get("case"))))
        out[b] = pairs
    out["live_only"] = {live_tr(x) for x in _ids(step.get("live_only"))}
    out["case_only"] = {ctx.to_global(x) for x in _ids(step.get("case_only"))}
    return out


def _gold_mapping(m) -> dict[str, set]:
    return {"matched": {(p.live, p.case) for p in m.matched}, "corresponding": {(p.live, p.case) for p in m.corresponding},
            "live_only": set(m.live_only), "case_only": set(m.case_only)}


def mapping_compare(ctx: ScoringContext, kind: str, **w) -> dict | None:
    """kind: "fact" | "consideration". -> {score, <bucket>: {key_only, both, agent_only}, translated: {...}}.
    None if the gold mapping is absent, nothing was served, or the live ids cannot be translated (no gold list)."""
    gold_m = ctx.key.fact_mapping if kind == "fact" else ctx.key.consideration_mapping
    al = ctx.fact_al if kind == "fact" else ctx.cons_al
    if gold_m is None or not ctx.served or al is None:
        return None
    tr = ctx.fact_tr if kind == "fact" else ctx.cons_tr
    step = ctx.step("fact_mapping" if kind == "fact" else "consideration_mapping")
    agent = _translate_mapping(ctx, step, tr)
    gold = _gold_mapping(gold_m)
    counts = {b: A.set_compare(gold[b], agent[b]) for b in BUCKETS}
    return {"score": A.set_score(list(counts.values()), **w), **counts,
            "translated": {b: sorted(map(str, agent[b])) for b in BUCKETS}}


# ---- Considerations enumeration (ENUM_GRADER + per-consideration SET_COMPARE)
def considerations_enumeration(ctx: ScoringContext, conditional: bool = False, **w) -> dict | None:
    """ENUM_GRADER over the consideration alignment, then for each gold consideration and its aligned agent
    consideration: SET_COMPARE on facts (translated) and favors (translated), exact match on equity and weight.
    Attribute scores average over all gold considerations (an unaligned one scores 0 on each) unless
    `conditional=True`, which averages over aligned pairs only."""
    al = ctx.cons_al
    if al is None:
        return None
    enum = A.enum_grade(al, **w)
    by_gold = {g: gen for g, gen, _ in al.pairs}
    agent = {c["id"]: c for c in ctx.agent_considerations}
    per = {}
    for gc in ctx.key.considerations:
        k = agent.get(by_gold.get(gc.id))
        if k is None:
            per[gc.id] = None
            continue
        fc = A.set_compare(gc.facts, {ctx.fact_tr(f) for f in _ids(k.get("facts"))})
        oc = A.set_compare(gc.favors, {ctx.opt_tr(o) for o in _ids(k.get("favors"))})
        per[gc.id] = {"facts": fc, "favors": oc, "facts_score": A.set_score(fc), "favors_score": A.set_score(oc),
                      "equity": int(_s(k.get("equity")) == gc.equity),
                      "weight": int(_s(k.get("weight")).lower() == gc.weight)}
    pairs = [v for v in per.values() if v]
    denom = len(pairs) if conditional else len(per)

    def avg(f):
        return (sum(v[f] for v in pairs) / denom) if denom else None

    return {"enum": enum, "facts": avg("facts_score"), "favors": avg("favors_score"), "equity": avg("equity"),
            "weight": avg("weight"), "per": per}


# ---- Applicability
def applicability_governs(ctx: ScoringContext) -> int | None:
    """exact_match(key.governs, applicability.governs) -> 0/1. Scored even when the agent declines: the decline
    itself is this row (it is not *after* not_governed)."""
    if ctx.key.governs is None:
        return None
    return int(_bool(ctx.step("applicability").get("governs")) is ctx.key.governs)


# ---- Verdict
def _resolve_choice(ctx: ScoringContext) -> tuple[str | None, str]:
    """Agent's verdict choice -> gold option id. -> (gold id | None, how)."""
    raw = ctx.step("verdict").get("choice")
    if isinstance(raw, dict):
        raw = raw.get("id") or raw.get("option")
    ch = _s(raw)
    if not ch:
        return None, "missing"
    if ch in ctx.agent_options:
        g = ctx.option_al.translation.get(ch)
        return g, ("aligned" if g else "agent option not aligned to any gold option")
    # The choice is not one of the agent's own option ids (free text, or an id it never enumerated): align the
    # choice text itself against the gold options with one Choice call.
    gold_ids = list(ctx.gold_options)
    dist = ctx.judge.choice(ch, [ctx.gold_options[g] for g in gold_ids], None, instruction("option"))
    best = max(range(len(gold_ids)), key=lambda i: dist[i])
    if dist[best] > ctx.threshold:
        return gold_ids[best], "choice text aligned directly"
    return None, "choice not among the agent's options and not alignable"


def verdict_choice(ctx: ScoringContext, gate: bool = True) -> int | None:
    """translate -> exact_match against key.choice / key.acceptable. -> 0/1. None after the agent's not_governed
    (when gate=True); `gate=False` is the ungated diagnostic for eval (e.g. Checkpoint 2 choice accuracy in the
    decoy arm), never for reward."""
    if gate and ctx.agent_not_governed:
        return None
    g, how = _resolve_choice(ctx)
    ctx.notes["choice"] = {"gold_id": g, "how": how}
    return int(ctx.key.correct(g))


def verdict_course(ctx: ScoringContext) -> float | None:
    if ctx.key.course is None or ctx.agent_not_governed:
        return None
    cand = _s(ctx.step("verdict").get("course"))
    return float(ctx.judge.noul(ctx.key.course, cand, noul_question("course"))) if cand else 0.0


def verdict_relation(ctx: ScoringContext) -> int | None:
    """exact_match(key.relation, verdict.relation). Scored even for not_governed (it is the decline itself)."""
    if ctx.key.relation is None:
        return None
    return int(_s(ctx.step("verdict").get("relation")).lower() == ctx.key.relation)


def _agent_via(ctx) -> list[str]:
    v = ctx.step("verdict").get("via")
    return [] if v in (None, "", "null", "none") else _ids(v)


def via_match(ctx: ScoringContext) -> int | None:
    """Agent's via (served ids -> global) == key.via (global), as sets. None when gold has no via (relation is not
    flips) or after the agent's not_governed."""
    if not ctx.key.via or ctx.agent_not_governed:
        return None
    return int({ctx.to_global(v) for v in _agent_via(ctx)} == set(ctx.key.via))


def via_consistent(ctx: ScoringContext) -> int | None:
    """Self-consistency, no gold needed: when the agent says `flips` with a via, its chosen option must be the
    cited would_change item's `then:`. Path: agent choice -> agent's own options map (fact_mapping.options) ->
    served option, compared with the served item's `then` (both translated to global ids). If the agent's map lacks
    its choice, fall back to agent choice -> gold option (alignment) -> key.option_map. Every cited item must agree.
    None when the agent does not claim flips with a via."""
    if ctx.agent_not_governed or _s(ctx.step("verdict").get("relation")).lower() != "flips":
        return None
    vias = _agent_via(ctx)
    if not vias:
        return None
    thens = []
    for v in vias:
        t = ctx.served_would_change.get(_s(v))
        if t is None:
            ctx.notes["via_consistent"] = {"path": "invalid via", "via": v}
            return 0
        thens.append(ctx.to_global(t))
    ch = _s(ctx.step("verdict").get("choice"))
    amap = ctx.step("fact_mapping").get("options")
    amap = amap if isinstance(amap, dict) else {}
    if ch in amap and amap[ch] not in (None, "", "null"):
        mapped, path = ctx.to_global(amap[ch]), "agent options map"
    else:
        g, _ = _resolve_choice(ctx)
        mapped = (ctx.key.option_map or {}).get(g) if g else None
        path = "gold option map (agent map lacks its choice)"
    ctx.notes["via_consistent"] = {"path": path, "choice_maps_to": mapped, "then": thens}
    return int(mapped is not None and all(t == mapped for t in thens))


def verdict_decisive(ctx: ScoringContext, **w) -> dict | None:
    """SET_COMPARE(key.decisive, agent decisive translated through the consideration alignment)."""
    if ctx.key.decisive is None or ctx.agent_not_governed or ctx.cons_al is None:
        return None
    c = A.set_compare(ctx.key.decisive, {ctx.cons_tr(x) for x in _ids(ctx.step("verdict").get("decisive"))})
    return {"score": A.set_score(c, **w), **c}


def verdict_now(ctx: ScoringContext, **w) -> A.EnumScore | None:
    """ENUM_GRADER over a judge alignment of the agent's `now` actions to the gold ones."""
    if ctx.key.now is None or ctx.agent_not_governed:
        return None
    gen = {f"now{n + 1}": _s(x.get("do") or x.get("what") or x) if isinstance(x, dict) else _s(x)
           for n, x in enumerate(_as_list(ctx.step("verdict").get("now")))}
    gold = {f"gold-now{n + 1}": x for n, x in enumerate(ctx.key.now)}
    al = A.align(gen, gold, ctx.judge, ctx.threshold, instruction("now"))
    ctx.notes["now_alignment"] = al.to_dict()
    return A.enum_grade(al, **w)


def _agent_flips(ctx, include_noflip: bool) -> list[dict]:
    fc = ctx.step("verdict").get("flip_conditions")
    if isinstance(fc, dict):
        items = _as_list(fc.get("would_change")) + (_as_list(fc.get("would_not_change")) if include_noflip else [])
    else:   # a flat list (seen from untrained Granite): items with `then` are would_change
        items = [x for x in _as_list(fc) if isinstance(x, dict) and (include_noflip or x.get("then"))]
    return [dict(x) for x in items if isinstance(x, dict)]    # copies: never mutate the parsed reply


def flip_text(cond, then_text) -> str:
    return f"If {_s(cond)}, then: {_s(then_text) or 'the choice does not change'}"


def verdict_flip_conditions(ctx: ScoringContext, **w) -> dict | None:
    """ENUM_GRADER over a judge alignment of the agent's would_change conditions to key.flip_conditions (the `if`
    plus the text of the `then` option), plus `then` accuracy on aligned pairs (agent then -> gold option by the
    option alignment), averaged over the gold flips that have a then."""
    if ctx.key.flip_conditions is None or ctx.agent_not_governed:
        return None
    gold_flips = ctx.key.flip_conditions
    include_noflip = any(f.then is None for f in gold_flips)
    agent = _agent_flips(ctx, include_noflip)
    gen = {}
    for n, x in enumerate(agent):
        i = _s(x.get("id")) or f"gen-flip{n + 1}"
        while i in gen:
            i += "'"
        then = _s(x.get("then"))
        gen[i] = flip_text(x.get("if") or x.get("what"), ctx.agent_options.get(then, then) if then else "")
        x["_id"] = i
    gold = {f.id: flip_text(f.if_, ctx.gold_options.get(f.then, f.then) if f.then else "") for f in gold_flips}
    al = A.align(gen, gold, ctx.judge, ctx.threshold, instruction("flip"))
    ctx.notes["flip_alignment"] = al.to_dict()
    by_gen = {x["_id"]: x for x in agent}
    with_then = [f for f in gold_flips if f.then]
    ok = 0
    for g, l, _ in al.pairs:
        gf = next(f for f in gold_flips if f.id == g)
        if gf.then and ctx.opt_tr(by_gen[l].get("then")) == gf.then:
            ok += 1
    return {"enum": A.enum_grade(al, **w), "then": ok / len(with_then) if with_then else None}
