"""SFT-building operator, step 1: the gold structure of one pairs-v1 cell (Peter, 2026-11-12).

A pairs-v1 cell is (X1 = the anchor, served as the live trace T(X1); X2 = the served case C(X2); arm). The SFT target
is the sequence  F, Q | M_F | K | M_K | applicability | W | V  for X1 informed by C(X2). This module builds everything in
it that is not prose, as a PairRecord (global ids), so `pipeline.solve.structure.GoldStructure` can renumber it to the
LIVE-* / REF1-* ids the student sees.

Two strategies behind one entry point, `pair_gold(store, cell)`:

    derived   X2 was made from X1 by a chain of operators. Every step recorded a delta (fact / consideration / option
              maps between its input and its output). They are put parent -> child and composed along the chain
              anchor -> ... -> X2: an item survives if every step maps it; a pair is `corresponding` if any step changed
              it, else `matched`; anchor items that fall out are live_only, X2 items never reached are case_only.
              Steps with no fact map (transfer, neighbor: new facts) leave the fact map to the `aligned` strategy.
    aligned   no usable lineage (random arm; facts of transfer / neighbor): an LLM aligner (role sft_aligner) proposes
              the buckets; the code checks they are one-to-one and complete.

Verdict side per arm (X1 is live, X2 is served):
    self, transfer, neighbor, noflip   follows; choice = X1's gold (checked: X2's gold is X1's gold under the option map)
    same_domain_flip, transfer_flip    flips via X2's back-flip item (the would_change item the flip operator wrote whose
                                       `then` is X1's gold under the option map; arms.augmented does the same)
    revised                            follows C' (R94): live K, decisive and flip conditions are C''s carried onto X1's
                                       facts (judgment_edit keeps ids), choice = the cell's key; consideration map matched
    random                             governs false, not_governed (the aligner must agree it does not govern; if it says
                                       it governs, the cell is skipped as ambiguous)
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from dataclasses import dataclass, field

import yaml

from bench.schema.pipeline import FrameCmp, GoldMap, GPair, PairRecord, Touched

BUCKET_RANK = {"matched": 0, "corresponding": 1}
SAME = FrameCmp(question="same", decider="same", role="same")
FOLLOWS_ARMS = {"self", "transfer", "neighbor", "noflip"}
FLIP_ARMS = {"same_domain_flip", "transfer_flip"}
DERIVED_ARMS = FOLLOWS_ARMS | FLIP_ARMS | {"revised"}
INTENT = {"self": "self", "transfer": "restyle", "neighbor": "restyle", "noflip": "add_fact", "same_domain_flip": "augmented",
          "transfer_flip": "augmented", "revised": "revised", "random": "decoy"}


class Skip(Exception):
    """The cell cannot get a gold (reason in the message); it is left out of SFT and listed."""


def loc(g: str) -> str:
    return g.rpartition("/")[2]


@dataclass
class Built:
    pair: PairRecord
    T: object                      # Scenario used as the live side (X1, or X1 with C''s A for revised)
    C: object                      # Scenario served (X2)
    strategy: dict = field(default_factory=dict)     # kind -> derived | aligned | identity
    notes: list[str] = field(default_factory=list)
    aligner: dict | None = None    # the aligner's raw output, when it ran


# ---------------------------------------------------------------------------------------------- derived: lineage
def _step_of(sc) -> dict:
    """The lineage step that produced scenario `sc` (its last step)."""
    steps = (sc.model_dump().get("lineage") or {}).get("steps") or []
    if not steps:
        raise Skip(f"{sc.id}: no lineage steps")
    return steps[-1]


def _ids(sc, kind: str) -> list[str]:
    c = sc.case
    return {"F": [f.id for f in c.facts], "C": [k.id for k in c.considerations], "O": list(c.options)}[kind]


def _step_map(step: dict, parent, child) -> dict:
    """parent-local -> (child-local, bucket) per kind, or None when the step has no map for that kind."""
    d = step.get("delta") or {}
    rev = step["op"] == "judgment_edit"            # the revise delta is written live = parent, case = child
    out = {}
    for kind, key in (("F", "fact_map"), ("C", "consideration_map")):
        if key not in d:                          # permute: facts and considerations keep their ids
            out[kind] = {i: (i, "matched") for i in _ids(parent, kind) if i in set(_ids(child, kind))}
        elif d[key] is None:
            out[kind] = None
        else:
            m = {}
            for b in ("matched", "corresponding"):
                for p in d[key].get(b) or []:
                    par, ch = (p["live"], p["case"]) if rev else (p["case"], p["live"])
                    m[loc(par)] = (loc(ch), b)
            out[kind] = m
    om = {}
    for a, b in (d.get("options_map") or {}).items():
        par, ch = (a, b) if rev else (b, a)
        if par is not None and ch is not None:
            om[loc(par)] = (loc(ch), "matched")
    out["O"] = om
    return out


def compose(store, chain: list[str]) -> dict:
    """anchor-local -> (X2-local, bucket) per kind along the chain; None for a kind some step left unmapped."""
    scs = [store.scenario(x) for x in chain]
    cur = {k: {i: (i, "matched") for i in _ids(scs[0], k)} for k in "FCO"}
    for parent, child in zip(scs, scs[1:]):
        sm = _step_map(_step_of(child), parent, child)
        for k in "FCO":
            if cur[k] is None:
                continue
            if sm[k] is None:
                cur[k] = None
                continue
            nxt = {}
            for a, (i, b) in cur[k].items():
                if i in sm[k]:
                    j, b2 = sm[k][i]
                    nxt[a] = (j, b if BUCKET_RANK[b] >= BUCKET_RANK[b2] else b2)
            cur[k] = nxt
    return cur


def _gold_map(m: dict, X1, X2, kind: str) -> GoldMap:
    a_all, b_all = _ids(X1, kind), _ids(X2, kind)
    g1, g2 = X1.case.global_id, X2.case.global_id
    hit = {j for j, _ in m.values()}
    return GoldMap(
        matched=[GPair(live=g1(a), case=g2(j)) for a, (j, b) in m.items() if b == "matched"],
        corresponding=[GPair(live=g1(a), case=g2(j)) for a, (j, b) in m.items() if b == "corresponding"],
        live_only=[g1(a) for a in a_all if a not in m], case_only=[g2(b) for b in b_all if b not in hit])


# ---------------------------------------------------------------------------------------------- aligned: LLM
PROMPTS = Path(__file__).parent / "prompts"
ALIGN_PROMPT = (PROMPTS / "aligner.v1.md").read_text()
CONS_BLOCK = (PROMPTS / "aligner_considerations_block.v1.md").read_text()


def _brief(sc) -> str:
    c = sc.case
    d = {"question": c.question, "decider": c.decider, "agent_role": c.agent,
         "facts": {f.id: f.fact for f in c.facts},
         "options": {k: o.do for k, o in c.options.items()},
         "considerations": {k.id: {"facts": list(k.facts), "equity": k.equity, "favors": list(k.favors),
                                   "weight": k.weight, "why": k.why} for k in c.considerations}}
    return yaml.safe_dump(d, sort_keys=False, allow_unicode=True, width=120)


def align(X1, X2, cons_known: dict | None, call=None) -> dict:
    """LLM alignment of X1 (live) with X2 (case). cons_known: anchor C -> (X2 C, bucket) when lineage gave it (then the
    model does facts only, with the consideration map shown as context)."""
    from bench.models import complete
    known = ""
    if cons_known is not None:
        pairs = [f"  {a} -> {j} ({b})" for a, (j, b) in cons_known.items()]
        known = ("\nThe consideration map is already known (from how CASE was built); use it to see which facts play the "
                 "same role:\n" + "\n".join(pairs) + "\n")
    prompt = ALIGN_PROMPT.format(known=known, x1=X1.id, x2=X2.id, live=_brief(X1), case=_brief(X2),
                                 cons_block="" if cons_known is not None else CONS_BLOCK)
    text = (call or (lambda m: complete("sft_aligner", m, stage="sft-align")))([{"role": "user", "content": prompt}])
    t = re.sub(r"^```(?:yaml)?\s*|\s*```\s*$", "", (text or "").strip())
    out = yaml.safe_load(t)
    if not isinstance(out, dict) or "facts" not in out:
        raise Skip(f"aligner gave no usable YAML for {X1.id} x {X2.id}")
    return out


def _from_aligner(pairs: dict, a_ids: list[str], b_ids: list[str], what: str) -> dict:
    m, used_b = {}, set()
    for b in ("matched", "corresponding"):
        for p in pairs.get(b) or []:
            if not (isinstance(p, (list, tuple)) and len(p) >= 2):
                raise Skip(f"aligner {what}: malformed pair {p!r}")
            x, y = (re.sub(r"^(LIVE|CASE)[\s-]*", "", str(v).strip()) for v in p[:2])
            if x not in a_ids or y not in b_ids:
                raise Skip(f"aligner {what}: unknown id in {p!r}")
            if x in m or y in used_b:
                raise Skip(f"aligner {what}: not one-to-one at {p!r}")
            m[x] = (y, b)
            used_b.add(y)
    return m


# ---------------------------------------------------------------------------------------------- entry point
def _with_A(X1, Cp):
    """X1 with C''s considerations, reasoning, verdict and flip conditions (revised arm; ids must be equal)."""
    from bench.schema import Case
    d, a = X1.case.dump(), Cp.case.dump()
    if set(d["options"]) != set(a["options"]) or [f["id"] for f in d["facts"]] != [f["id"] for f in a["facts"]]:
        raise Skip(f"revised: {Cp.id} does not keep {X1.id}'s fact and option ids")
    for k in ("considerations", "reasoning", "verdict", "flip_conditions", "lesson", "limits"):
        d[k] = a[k]
    return X1.model_copy(update={"case": Case.model_validate(d)})


def pair_gold(store, cell: dict, equities: str = "pilot2", call=None, aligned: dict | None = None) -> Built:
    """aligned: a stored aligner output to reuse instead of calling the aligner again."""
    arm, x1, x2, chain = cell["arm"], cell["x1"], cell["x2"], cell["chain"]
    X1, X2 = store.scenario(x1), store.scenario(x2)
    notes, strategy, aligner = [], {}, None
    g1, g2 = X1.case.global_id, X2.case.global_id

    if arm == "random":
        aligner = aligned or align(X1, X2, None, call)
        if aligner.get("governs") is not False:
            raise Skip(f"random: the aligner says {x2} governs {x1} ({aligner.get('governs_why')}); ambiguous, left out")
        fm = _from_aligner(aligner["facts"], _ids(X1, "F"), _ids(X2, "F"), "facts")
        cm = _from_aligner(aligner.get("considerations") or {}, _ids(X1, "C"), _ids(X2, "C"), "considerations")
        om = {}
        strategy = {"F": "aligned", "C": "aligned", "O": "none (not governed)"}
        frame = FrameCmp(**aligner["frame"])
        T = X1
        governs, relation, via, choice = False, "not_governed", None, g1(X1.case.verdict.choice)
        touched = None
    elif arm in DERIVED_ARMS:
        path = chain if arm != "self" else [x1]
        if path[0] != x1 or path[-1] != x2:
            raise Skip(f"chain {path} does not run from X1 to X2")
        comp = compose(store, path)
        om, cm, fm = comp["O"], comp["C"], comp["F"]
        strategy = {k: "derived" for k in "FCO"}
        if arm == "self":
            strategy = {k: "identity" for k in "FCO"}
        if cm is None:
            raise Skip("no consideration map along the chain")
        if set(om) != set(_ids(X1, "O")):
            raise Skip(f"option map along the chain is incomplete: {sorted(set(_ids(X1, 'O')) - set(om))} unmapped")
        frame = SAME
        if fm is None:                               # transfer / neighbor: facts are new
            aligner = aligned or align(X1, X2, cm, call)
            fm = _from_aligner(aligner["facts"], _ids(X1, "F"), _ids(X2, "F"), "facts")
            strategy["F"] = "aligned"
            frame = FrameCmp(**aligner["frame"])
        T = X1
        x1_choice = X1.case.verdict.choice
        x2_choice = X2.case.verdict.choice
        touched = None
        if arm in FOLLOWS_ARMS:
            if om[x1_choice][0] != x2_choice:
                raise Skip(f"{arm}: X2's gold {x2_choice} is not X1's gold {x1_choice} under the option map")
            relation, via, choice = "follows", None, g1(x1_choice)
            if arm == "noflip":
                st = [s for s in (store.scenario(c) for c in path[1:]) if (_step_of(s).get("delta") or {}).get("touched")]
                if st:
                    t = _step_of(st[0])["delta"]["touched"]
                    item = loc(t["item"]) if t.get("item") else None
                    wn = {w.id for w in X2.case.flip_conditions.would_not_change}
                    touched = Touched(item=g2(item) if item in wn else None, condition=t["condition"], how=t["how"])
        elif arm in FLIP_ARMS:
            back = om[x1_choice][0]
            items = [w for w in X2.case.flip_conditions.would_change if w.then == back]
            if not items:
                raise Skip(f"{arm}: X2 has no would_change item with then = {back} (X1's gold {x1_choice})")
            relation, via, choice = "flips", [g2(w.id) for w in items], g1(x1_choice)
            if len(items) > 1:
                notes.append(f"{len(items)} back-flip items; all listed in via")
            w = items[0]
            touched = Touched(item=g2(w.id), condition=w.if_, how="the condition the flip made true in the case does not "
                              "hold in the live situation")
        else:                                        # revised: X1's facts, C''s judgment
            cp = store.scenario(path[1])
            if "judgment_edit" != _step_of(cp)["op"]:
                raise Skip(f"revised: {path[1]} is not a judgment_edit output")
            T = _with_A(X1, cp)
            key = cell.get("key")
            if not key or cell.get("key_source") == "UNMAPPED":
                raise Skip("revised: no cell key")
            if T.case.verdict.choice != key:
                raise Skip(f"revised: C' verdict {T.case.verdict.choice} != cell key {key}")
            cm = {i: (j, "matched") for i, (j, _) in cm.items()}    # live K is C''s K: same weights as the case
            relation, via, choice = "follows", None, g1(key)
            dk = (_step_of(cp).get("delta") or {}).get("touched") or {}
            touched = Touched(item=None, condition=dk.get("condition", "the revised weighing"),
                              how=dk.get("how", "re-weighted"))
            notes.append("revised: live K / decisive / flip conditions are C''s on X1's facts (R94)")
        governs = True
    else:
        raise Skip(f"arm {arm} has no SFT gold builder")

    pair = PairRecord(
        id=f"SFT-{cell['cell']}", intent=INTENT[arm], arm="relevant", card_view="full",
        ar_prompt=True, case_scenario=x2, trace_scenario=x1, split=X1.split, equities=equities, frame=frame,
        options_map={g1(a): (g2(om[a][0]) if a in om else None) for a in _ids(X1, "O")},
        fact_map=_gold_map(fm, T, X2, "F"), consideration_map=_gold_map(cm, T, X2, "C"),
        governs=governs, relation=relation, via=via, choice=choice, acceptable=[],
        gold_tier=(X1.verdict_tier if X1.verdict_tier in ("by-construction", "source-endorsed", "model-solved") else "by-construction"), touched=touched, trace_ref=x1,
        tags=["sft-pairgold", f"pv1-arm:{arm}"] + [f"{k}:{v}" for k, v in strategy.items()])
    return Built(pair=pair, T=T, C=X2, strategy=strategy, notes=notes, aligner=aligner)
