#!/usr/bin/env python3
"""Score cheap, reasoning-free mapping policies with the MVP scorer (code/mvp.py, unmodified).

Scenario pool:
  - the 13 live scenarios on disk (AUT-101 cross + 6 flip + 6 novel variants from the fit test)
  - 7 "restyle proxies": each reference's own scenario used as a live scenario, gold = the
    reference's choice, relation follows, nothing planted. This is what restyle/stronger/trap
    variants look like to the scorer (gold is the reference's choice by construction).
  - decoy condition: each of the 13 live scenarios served a different reference.

Every generated mapping passes the format gate. None of them reads the situation for meaning.
Run: python3 review/policies.py   (from the mvp/ folder)
"""
import copy
import glob
import os
import re
import sys

import yaml

HERE_DIR = os.path.dirname(os.path.abspath(__file__))
MVP = os.path.dirname(HERE_DIR)
sys.path.insert(0, os.path.join(MVP, "code"))
import mvp  # noqa: E402

CONF = 0.75  # one constant confidence for every policy (the Brier term is then a constant tax)


def load(p):
    with open(p) as f:
        return yaml.safe_load(f)


def pool():
    items = []
    lives = [os.path.join(MVP, "examples/AUT-101.live.yaml")] + sorted(glob.glob(os.path.join(MVP, "fit-test/v2/*.live.yaml")))
    refs = {}
    for p in [os.path.join(MVP, "examples/AUT-001.reference.yaml")] + sorted(glob.glob(os.path.join(MVP, "fit-test/v2/*.reference.yaml"))):
        d = load(p)
        refs[d["id"]] = d
    for p in lives:
        live = load(p)
        items.append(("live", live["id"], live, refs[live["reference"]]))
    for rid, ref in refs.items():
        live = {"id": rid + "-restyle", "reference": rid, "variant": "restyle", "decoys": [],
                "scenario": copy.deepcopy(ref["scenario"]),
                "gold": {"choice": ref["resolution"]["choice"], "acceptable": [ref["resolution"]["choice"]],
                         "relation": "follows", "planted": [], "why": "restyle proxy", "basis": "recommended"}}
        items.append(("restyle", live["id"], live, ref))
    return items, refs


# ---------------------------------------------------------------- choice rules (no reading)
def handup_options(opts):
    return [k for k, o in opts.items() if o.get("move") in ("ask", "partial")]


def choose_handup_only(live, ref):
    """Literal 'always pick the ask/partial option'; else a refuse option; else option A."""
    opts = live["scenario"]["options"]
    hu = handup_options(opts)
    if hu:
        return hu[0]
    ref_ = [k for k, o in opts.items() if o.get("move") == "refuse"]
    return ref_[0] if ref_ else "A"


def choose_handup_else_follow(live, ref):
    """Pick the ask/partial option; if there is none, pick the reference's choice letter."""
    opts = live["scenario"]["options"]
    hu = handup_options(opts)
    if hu:
        return hu[0]
    rc = ref["resolution"]["choice"]
    return rc if rc in opts else "A"


def choose_follow(live, ref):
    opts = live["scenario"]["options"]
    rc = ref["resolution"]["choice"]
    return rc if rc in opts else "A"


def choose_A(live, ref):
    return "A"


STOP = set("a an the of to and or in on at is are was be it its this that for with as by from not no if than "
           "only can could will would may his her he she they them their there here one any all has have had "
           "more less who what when which".split())


def toks(s):
    return {w for w in re.findall(r"[a-z]+", str(s).lower()) if w not in STOP and len(w) > 2}


def choose_lookup(live, ref):
    """Lexical boundary lookup: flip to a would_change item whose `if` words newly appear in the live
    situation (words not in the reference situation); prefer `ask` when several items fire."""
    opts = live["scenario"]["options"]
    rc = ref["resolution"]["choice"]
    lt = toks(live["scenario"].get("situation", ""))
    rt = toks(ref["scenario"].get("situation", ""))
    fired = []
    for w in ref["resolution"]["boundaries"]["would_change"]:
        it = toks(w["if"])
        new = (it & lt) - rt
        if it and len(new) / len(it) >= 0.25:
            fired.append(w["then"])
    if fired:
        t = "ask" if "ask" in fired else fired[0]
        if t == "ask":
            hu = handup_options(opts)
            return hu[0] if hu else (rc if rc in opts else "A")
        return t if t in opts else "A"
    return rc if rc in opts else "A"


# ---------------------------------------------------------------- mapping builder
def build(live, ref, choice, *, heuristics=True, enumerate_new=False, decoy_guess=False):
    """A gate-valid mapping that carries no reasoning. With heuristics=True the anchors are set by
    content-free rules keyed only on whether `choice` equals the reference's choice letter."""
    res = ref["resolution"]
    rc = res["choice"]
    lopts = live["scenario"]["options"]
    ropts = ref["scenario"]["options"]
    omap = {k: (k if k in ropts else None) for k in lopts}
    departs = omap.get(choice) != rc
    # decoy guess: lexical overlap between the served card's situation and the live one
    jac = len(toks(live["scenario"].get("situation", "")) & toks(ref["scenario"].get("situation", ""))) / max(
        1, len(toks(live["scenario"].get("situation", "")) | toks(ref["scenario"].get("situation", ""))))
    is_decoy_guess = decoy_guess and jac < 0.15
    comp, new = [], []
    for i, c in enumerate(res["considerations"]):
        if heuristics and departs and not is_decoy_guess:
            here = "weaker" if c["favors"] == rc else "stronger"
            matters = "decides" if (c["favors"] == rc and not any(x["matters"] == "decides" for x in comp)) else "weighs"
        else:
            here, matters = "same", "weighs"
        comp.append({"ref": c["id"], "live": "x", "here": here, "matters": matters, "why": "."})
    if heuristics and not is_decoy_guess:
        for v in ("lawful_authority", "chain_of_command"):
            new.append({"live": "x", "favors": choice, "value": v, "matters": "weighs", "why": "."})
    if enumerate_new:
        for o in lopts:
            for v in sorted(mvp.VALUES):
                new.append({"live": "x", "favors": o, "value": v, "matters": "no", "why": "."})
    if is_decoy_guess:
        rel = "not_governed"
    elif heuristics and departs:
        rel = "flips"
        # a flip needs one `decides` against the reference's choice; the compare line above supplies it
        # unless the reference has no consideration favoring its own choice (never true here)
    else:
        rel = "follows"
    return {"mapping": {
        "frame": {"question": "x", "owner": "x", "my_role": "x", "values": []},
        "fit": {"case": ref["id"], "rating": "poor", "why": "x", "options": omap},
        "compare": comp,
        "new": new,
        "carry": {"relation": rel, "settled": ".", "open": "."},
        "decide": {"choice": choice, "confidence": CONF, "now": ".", "would_change_my_mind": ""},
    }}


def run():
    items, refs = pool()
    policies = {
        "handup_only (bare)": dict(choose=choose_handup_only, heuristics=False),
        "handup_only + anchor heuristics": dict(choose=choose_handup_only, heuristics=True),
        "handup_else_follow + heuristics": dict(choose=choose_handup_else_follow, heuristics=True),
        "handup_else_follow + heuristics + enumerate new": dict(choose=choose_handup_else_follow, heuristics=True, enumerate_new=True),
        "follow_reference (bare)": dict(choose=choose_follow, heuristics=False),
        "always_A + heuristics": dict(choose=choose_A, heuristics=True),
        "lexical_lookup + heuristics": dict(choose=choose_lookup, heuristics=True),
    }
    out = []
    table = {}
    for name, cfg in policies.items():
        rows = []
        for kind, iid, live, ref in items:
            ch = cfg["choose"](live, ref)
            m = build(live, ref, ch, heuristics=cfg["heuristics"], enumerate_new=cfg.get("enumerate_new", False))
            s = mvp.score(m, live, ref)
            if s["gate"] != 1:
                raise SystemExit(f"{name} {iid}: gate failed {s['errors']}")
            rows.append((kind, iid, ch, live["gold"]["choice"], s))
        table[name] = rows
    # gold mappings for the 13 live scenarios
    gold_rows = []
    for kind, iid, live, ref in items:
        if kind != "live":
            continue
        folder = os.path.join(MVP, "examples") if iid == "AUT-101" else os.path.join(MVP, "fit-test/v2")
        m = load(os.path.join(folder, iid + ".mapping.yaml"))
        gold_rows.append((kind, iid, m["mapping"]["decide"]["choice"], live["gold"]["choice"], mvp.score(m, live, ref)))

    def summ(rows, kind):
        rr = [r for r in rows if r[0] == kind]
        if not rr:
            return ""
        acc = sum(r[4]["outcome"] > 0 for r in rr)
        wa = sum(bool(r[4].get("wrongful_act")) for r in rr)
        mean = sum(r[4]["total"] for r in rr) / len(rr)
        return f"{acc}/{len(rr)} right, {wa} wrongful_act, mean reward {mean:.3f}"

    out.append("POLICY RESULTS (scorer: code/mvp.py score, unmodified; every mapping passes the gate)")
    out.append("Ceiling: 1.6 on live scenarios with planted items; 1.3 on restyle proxies (nothing planted).")
    out.append("")
    out.append(f"{'gold mappings (the agents own)':52} live: {summ(gold_rows, 'live')}")
    for name, rows in table.items():
        out.append(f"{name:52} live: {summ(rows, 'live')}")
        out.append(f"{'':52} restyle proxies: {summ(rows, 'restyle')}")
    out.append("")
    out.append("Per-scenario detail, policy 'handup_else_follow + heuristics':")
    for kind, iid, ch, g, s in table["handup_else_follow + heuristics"]:
        out.append(f"  {iid:16} pick={ch} gold={g}  total={s['total']:+.3f}  outcome={s['outcome']:+.0f}  "
                   f"relation={s['relation']:.0f}  differences={s.get('differences', '-')}")
    # decoy condition: serve every live scenario a different reference
    out.append("")
    out.append("DECOY CONDITION (each live scenario served the next reference in the list)")
    ids = sorted(refs)
    for pol_name, choose in [("handup_else_follow, lexical decoy guess", choose_handup_else_follow)]:
        rows = []
        for kind, iid, live, ref in items:
            if kind != "live":
                continue
            dec = refs[ids[(ids.index(ref["id"]) + 1) % len(ids)]]
            ch = choose(live, ref)  # the choice rule never reads the card anyway
            m = build(live, dec, ch, heuristics=True, decoy_guess=True)
            s = mvp.score(m, live, dec)
            rows.append((iid, dec["id"], ch, live["gold"]["choice"], s))
        mean = sum(r[4]["total"] for r in rows) / len(rows)
        acc = sum(r[4]["outcome"] > 0 for r in rows)
        rel = sum(r[4]["relation"] for r in rows)
        out.append(f"  {pol_name}: {acc}/{len(rows)} right, relation not_governed {rel:.0f}/{len(rows)}, "
                   f"fit poor {sum(r[4].get('fit', 0) for r in rows):.0f}/{len(rows)}, mean reward {mean:.3f} (ceiling 1.6)")
    # the same policy on the right card with lexical decoy guessing on (false-positive check)
    fp = 0
    for kind, iid, live, ref in items:
        m = build(live, ref, choose_handup_else_follow(live, ref), heuristics=True, decoy_guess=True)
        fp += m["mapping"]["carry"]["relation"] == "not_governed"
    out.append(f"  lexical decoy guess fires on the RIGHT card in {fp}/{len(items)} scenarios (false positives)")
    return "\n".join(out)


if __name__ == "__main__":
    text = run()
    print(text)
    with open(os.path.join(HERE_DIR, "policy_results.txt"), "w") as f:
        f.write(text + "\n")
