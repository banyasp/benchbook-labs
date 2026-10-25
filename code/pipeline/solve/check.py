"""Acceptance of a teacher sample against the gold structure.

Accepted iff (hard checks): the reply parses strictly (all required steps, valid, no repairs), and it matches gold on
the verdict choice (or an acceptable one), relation, via, governs, the options map, the enumerated fact and
consideration ids, and the fact / consideration mapping buckets (matched, corresponding, live_only, case_only).
Ids are compared after renumbering to global ids (LIVE-* through the live table, REF1-* through the served table).
Soft flags (logged in the sample file, not rejecting): frame comparisons, decisive set, whether the touched condition is
cited in the prose, schema words or teacher talk in the prose, length.
"""
from __future__ import annotations

import re

from bench.schema import parse_reply

from .structure import GoldStructure

SCHEMA_WORDS = re.compile(r"\b(gold|answer key|the key|teacher|touched|ground truth|was given to me)\b", re.I)


def clean_reply(text: str) -> str:
    """The documents only: drop anything before the first `kind:` line, code fences and trailing prose."""
    lines = [l for l in (text or "").splitlines() if not l.strip().startswith("```")]
    start = next((i for i, l in enumerate(lines) if re.match(r"^kind:\s*['\"]?[A-Za-z_]+['\"]?\s*$", l)), None)
    if start is None:
        return ""
    lines = lines[start:]
    top = re.compile(r"^([a-z_][a-z0-9_]*:(\s|$)|-(\s|$)|---+\s*$|#)")
    out = list(lines)
    while out:                                   # trim trailing prose (column-0 lines that are not yaml)
        l = out[-1]
        if not l.strip() or not (l[:1].isspace() or top.match(l)):
            out.pop()
        else:
            break
    while out and (not out[-1].strip() or out[-1].strip().startswith("---")):
        out.pop()
    return "\n".join(out).strip() + "\n"


def _s(x):
    return "" if x is None else str(x).strip()


def _lst(x):
    if x is None:
        return []
    return x if isinstance(x, list) else [x]


def check_reply(text: str, g: GoldStructure) -> dict:
    """-> {accepted, reasons, flags, clean, parsed}"""
    clean = clean_reply(text)
    p = parse_reply(clean)
    reasons: list[str] = []
    flags: dict = {}
    if not clean:
        return {"accepted": False, "reasons": ["no documents"], "flags": {}, "clean": "", "parsed": p}
    if not p.strict_ok:
        why = []
        if p.missing:
            why.append(f"missing {p.missing}")
        why += [f"{k}: {v[:100]}" for k, v in p.errors.items() if k in p.required() and k not in p.missing]
        if any(p.repairs.values()):
            why.append("repairs " + str({k: v for k, v in p.repairs.items() if v})[:120])
        if p.unknown_kinds:
            why.append(f"unknown kinds {p.unknown_kinds}")
        reasons.append("parse: " + "; ".join(why))
    st = p.steps
    to_g = {**g.live, **g.served.table}
    G = lambda x: to_g.get(_s(x), "untranslated:" + _s(x))
    gold_g = lambda x: to_g[x]

    def pairs(step, b):
        out = set()
        for it in _lst(st.get(step, {}).get(b)):
            if isinstance(it, dict):
                out.add((G(it.get("live")), G(it.get("case"))))
        return out

    def singles(step, b):
        out = set()
        for it in _lst(st.get(step, {}).get(b)):
            out.add(G(it.get("case") if isinstance(it, dict) else it))
        return out

    # enumerations
    fe = st.get("fact_enumeration", {})
    got = {_s(f.get("id")) for f in _lst(fe.get("facts")) if isinstance(f, dict)}
    if got != set(g.fact_order):
        reasons.append(f"fact ids: extra {sorted(got - set(g.fact_order))} missing {sorted(set(g.fact_order) - got)}")
    got = {_s(c.get("id")) for c in _lst(st.get("consideration_enumeration", {}).get("considerations")) if isinstance(c, dict)}
    if got != set(g.cons_ids):
        reasons.append(f"consideration ids: extra {sorted(got - set(g.cons_ids))} missing {sorted(set(g.cons_ids) - got)}")
    # verdict
    v = st.get("verdict", {})
    ok_choice = {g.choice, *g.acceptable}
    if _s(v.get("choice")) not in ok_choice:
        reasons.append(f"choice {_s(v.get('choice'))} != gold {g.choice}")
    if _s(v.get("relation")).lower() != g.pair.relation:
        reasons.append(f"relation {_s(v.get('relation'))} != gold {g.pair.relation}")
    via = {G(x) for x in _lst(v.get("via")) if _s(x)}
    if via != {gold_g(x) for x in g.via}:
        reasons.append(f"via {sorted(via)} != gold {sorted(gold_g(x) for x in g.via)}")
    gov = st.get("applicability", {}).get("governs")
    if gov is not g.pair.governs:
        reasons.append(f"governs {gov} != gold {g.pair.governs}")
    # options map
    om = st.get("fact_mapping", {}).get("options") or {}
    gm = {o: (s if s else None) for o, s in g.options_map.items()}
    if {_s(k): (_s(x) or None) for k, x in om.items()} != gm:
        reasons.append(f"options map {om} != gold {gm}")
    # buckets
    for name, step, gold in (("fact", "fact_mapping", g.fact_map), ("consideration", "consideration_mapping", g.cons_map)):
        for b in ("matched", "corresponding"):
            gp = {(gold_g(a), gold_g(c)) for a, c in gold[b]}
            if pairs(step, b) != gp:
                reasons.append(f"{name} {b}: got {sorted(pairs(step, b))} gold {sorted(gp)}")
        if singles(step, "live_only") != {gold_g(x) for x in gold["live_only"]}:
            reasons.append(f"{name} live_only differs")
        if singles(step, "case_only") != {gold_g(x) for x in gold["case_only"]}:
            reasons.append(f"{name} case_only differs")
    # soft flags
    for step in ("fact_mapping", "applicability"):
        fr = st.get(step, {}).get("frame") or {}
        if {k: _s(x) for k, x in fr.items()} != g.pair.frame.model_dump():
            flags[f"frame_{step}"] = "differs from gold"
    if {G(x) for x in _lst(v.get("decisive"))} != {gold_g(x) for x in g.decisive}:
        flags["decisive"] = "differs from gold"
    prose = " ".join(_s(x) for k in ("applicability", "reasoning") for x in (st.get(k) or {}).values()
                     if isinstance(x, (str, int)))
    for k in ("fact_mapping", "consideration_mapping"):
        prose += " " + " ".join(_s(i.get(f)) for b in ("matched", "corresponding") for i in _lst(st.get(k, {}).get(b))
                                if isinstance(i, dict) for f in ("note", "role"))
    t = g.pair.touched
    if t and t.item:
        sid = g.case2served.get(t.item)
        flags["touched_cited"] = bool(sid and re.search(rf"{re.escape(sid)}(?![\w])", prose))
    sw = SCHEMA_WORDS.findall(prose)
    if sw:
        flags["schema_words"] = sorted({w.lower() for w in sw})
    flags["words"] = len(clean.split())
    return {"accepted": not reasons, "reasons": reasons, "flags": flags, "clean": clean, "parsed": p}
