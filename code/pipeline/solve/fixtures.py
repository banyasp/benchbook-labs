"""Hand-made fixtures for P3 tests and the live check (P1/P2 outputs do not exist yet).

journalist_pair()  C = the PDF REF1 case (USV and the life raft), T = the PDF journalist scenario; the gold mapping is
                   the PDF's own (journalist.answer_key.yaml). End-to-end fixture. -> (store, pair_id)
flip_pair()        C = pilot INT-301 (militia), T = a restyled-and-flipped variant (a foreign power directs the group;
                   flip1 -> O1), with matched / corresponding facts. Exercises `via`.
mock_render_llm()  an offline renderer: one user message per fact carrying the fact in plain words.
synth_reply()      a gold-consistent reply (all seven documents) built from a GoldStructure, for offline tests.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from bench.schema import Case
from bench.schema.pipeline import GoldMap, GPair, PairRecord, Scenario, SourceRef, Touched
from pipeline.store import Store

ROOT = Path(__file__).resolve().parents[3]
PDF = ROOT / "code" / "bench" / "fixtures" / "pdf_example"
INT301 = ROOT / "data" / "cases" / "INT-301" / "DR-INT-301@v1.case.yaml"
C_PDF = "DR-PDF-001@v1"
T_JRN = "DR-PDF-JRN@v1"


def _docs(path) -> dict:
    out = {}
    for d in yaml.safe_load_all(Path(path).read_text()):
        out[d["kind"]] = d
    return out


def _scen(case: Case, family, split="eval-only", tier="source-endorsed") -> Scenario:
    return Scenario(id=case.id, family=family, split=split, domain="fixture", case=case, verdict_tier=tier,
                    basis="fixture", source=SourceRef(sha256="0" * 64, doc="000000000000.jsonl"))


def journalist_case() -> Case:
    d = _docs(PDF / "journalist.reply.yaml")
    fe, cons, rs, vd = d["fact_enumeration"], d["consideration_enumeration"], d["reasoning"], d["verdict"]
    strip = lambda s: s.replace("LIVE-", "")
    opts = {"O1": {"do": fe["options"]["LIVE-O1"], "move": "partial", "to": "partner liaison desk"},
            "O2": {"do": fe["options"]["LIVE-O2"], "move": "act"},
            "O3": {"do": fe["options"]["LIVE-O3"], "move": "act", "irreversible": True}}
    fl = vd["flip_conditions"]
    case = {
        "id": T_JRN, "title": "Journalist warning", "status": "reviewed",
        "setting": "A port city; signals collection support to an armed-group watch. Night shift, the day before the planned attack.",
        "decider": fe["frame"]["decider"], "agent": fe["frame"]["my_role"], "agent_role": "decide",
        "situation": " ".join(f["fact"] for f in fe["facts"]), "question": fe["frame"]["question"], "options": opts,
        "facts": [{"id": strip(f["id"]), "kind": f["kind"], "status": f["status"], "fact": f["fact"]} for f in fe["facts"]],
        "considerations": [{"id": strip(c["id"]), "facts": [strip(x) for x in c["facts"]], "equity": c["equity"],
                            "favors": [strip(x) for x in c["favors"]], "weight": c["weight"], "why": c["why"]}
                           for c in cons["considerations"]],
        "reasoning": {"read": "A warning may look like it exposes the channel, but she dies tomorrow without one.",
                      "weighing": rs["weighing"], "tradecraft": rs["tradecraft"], "uncertainty": rs["uncertainty"],
                      "handoff": rs["handoff"],
                      "tempting_wrong": {"option": "O1", "pull": rs["tempting_wrong"]["pull"],
                                         "why_wrong": rs["tempting_wrong"]["why_wrong"]},
                      "rejected": {"O2": rs["rejected"]["LIVE-O2"]}},
        "verdict": {"choice": "O3", "basis": "recommended", "decisive": ["C1"]},
        "flip_conditions": {
            "would_change": [{"id": "flip1", "if": fl["would_change"][0]["if"], "then": "O1", "why": fl["would_change"][0]["why"]},
                             {"id": "flip2", "if": fl["would_change"][1]["if"], "then": "O2", "why": fl["would_change"][1]["why"]}],
            "would_not_change": [{"id": "noflip1", "if": fl["would_not_change"][0]["if"], "why": fl["would_not_change"][0]["why"]}],
            "watch_for": [{"id": "watch1", "what": fl["watch_for"][0]["what"], "favors": ["O1", "O2"], "why": fl["watch_for"][0]["why"]}]},
        "lesson": "Warn when yours is the only warning in time.", "limits": "Not where the partner can warn her first.",
    }
    return Case.model_validate(case)


def journalist_pair(tmp) -> tuple[Store, str]:
    st = Store(tmp)
    C = _scen(Case.load(PDF / "REF1.case.yaml"), "PDF-001")
    T = _scen(journalist_case(), "PDF-JRN")
    st.save_scenario(C)
    st.save_scenario(T)
    key = yaml.safe_load((PDF / "journalist.answer_key.yaml").read_text())
    fm, cm = key["fact_mapping"], key["consideration_mapping"]
    gp = lambda xs: [GPair(live=f"{T_JRN}/{x['live'].replace('LIVE-', '')}", case=x["case"]) for x in xs]
    tl = lambda xs: [f"{T_JRN}/{x.replace('LIVE-', '')}" for x in xs]
    pair = PairRecord(
        id="P-pdfjrn", intent="pilot", case_scenario=C_PDF, trace_scenario=T_JRN, split="eval-only",
        frame=key["frame_map"],
        options_map={f"{T_JRN}/{k.replace('LIVE-', '')}": v for k, v in key["option_map"].items()},
        fact_map=GoldMap(matched=gp(fm["matched"]), corresponding=gp(fm["corresponding"]), live_only=tl(fm["live_only"]),
                         case_only=fm["case_only"]),
        consideration_map=GoldMap(matched=gp(cm["matched"]), live_only=tl(cm["live_only"])),
        governs=True, relation="follows", choice=f"{T_JRN}/O3", gold_tier="source-endorsed",
        touched=Touched(item=f"{C_PDF}/C1", condition="the asset is the only help that can reach the person in time",
                        how="carried to another domain (fixture)"))
    st.save_pair(pair)
    return st, pair.id


def flip_pair(tmp) -> tuple[Store, str]:
    st = Store(tmp)
    c = Case.load(INT301)
    C = _scen(c, "INT-301")
    d = c.dump()
    d["id"] = "DR-INT-301-fl1@v1"
    d["facts"][1]["fact"] = "The Tri-County Defense Force is a militia in the surrounding county."
    d["facts"][4]["fact"] = ("A seized phone shows the group's leader takes direction and money from a foreign "
                             "government's officer; the members still appear to be U.S. persons.")
    d["verdict"] = {"choice": "O1", "basis": "settled", "decisive": ["C2", "C5"]}
    d["considerations"][3]["why"] = "with a foreign direction the threat is inside the intelligence mission"
    d["considerations"][4]["favors"] = ["O1"]
    d["considerations"][4]["weight"] = "weak"
    d["considerations"][4].pop("rules_out", None)
    d["library"] = {}
    T = _scen(Case.model_validate(d), "INT-301", tier="by-construction")
    st.save_scenario(C)
    st.save_scenario(T)
    cg, tg = c.global_id, T.case.global_id
    pair = PairRecord(
        id="P-int301fl", intent="flip", case_scenario=c.id, trace_scenario=T.id, split="eval-only",
        frame={"question": "same", "decider": "same", "role": "same"},
        options_map={tg(o): cg(o) for o in ("O1", "O2", "O3")},
        fact_map=GoldMap(matched=[GPair(live=tg(f), case=cg(f)) for f in ("F1", "F3", "F4", "F6", "F7", "F8", "F9", "F10")],
                         corresponding=[GPair(live=tg("F2"), case=cg("F2"), note="reworded"),
                                        GPair(live=tg("F5"), case=cg("F5"), note="now a foreign tie")]),
        consideration_map=GoldMap(matched=[GPair(live=tg(f"C{i}"), case=cg(f"C{i}")) for i in (1, 2, 3, 4, 6)],
                                  corresponding=[GPair(live=tg("C5"), case=cg("C5"), note="no longer a bar")]),
        governs=True, relation="flips", via=[cg("flip1")], choice=tg("O1"), gold_tier="by-construction",
        touched=Touched(item=cg("flip1"), condition="the group is directed by a foreign power",
                        how="realized indirectly: a seized phone shows a foreign officer directing the leader"))
    st.save_pair(pair)
    return st, pair.id


def mock_render_llm(T: Scenario, order=None):
    """Offline renderer: system prompt, one message per fact (in `order`, default scenario order), a routine ping."""
    facts = list(T.case.facts)
    if order:
        facts = [next(f for f in facts if f.id == i) for i in order]

    def llm(role, messages, **kw):
        msgs = [{"role": "system", "content": "You are the workflow agent. Tools: msg.send(to, body), log.write(entry)."}]
        quotes = []
        for f in facts:
            msgs.append({"role": "user", "name": "ops", "time": "10:00", "content": f"Update {len(msgs)}: {f.fact} Routine ping follows."})
            quotes.append({"id": f.id, "realization": "stated", "quotes": [{"message": len(msgs) - 1, "quote": f.fact}]})
        msgs.append({"role": "tool", "name": "log.write", "content": "ok"})
        return json.dumps({"messages": msgs, "facts": quotes, "allowed": ["a ping at 10:00"], "planted": []})
    return llm


def synth_reply(g, mutate=None) -> str:
    """A valid, gold-consistent reply for GoldStructure g (teacher stand-in). mutate(dict_of_docs) may break it."""
    T, tb = g.T.case, g.served.table
    inv = {v: k for k, v in tb.items()}
    docs = {}
    docs["fact_enumeration"] = {"kind": "fact_enumeration",
        "frame": {"question": T.question, "decider": T.decider, "my_role": T.agent},
        "facts": [{"id": f, "kind": g.fact(f).kind, "status": g.fact(f).status, "fact": g.fact(f).fact} for f in g.fact_order],
        "options": {o: T.options[o.replace("LIVE-", "")].do for o in g.option_ids}}
    fm = g.fact_map
    pm = lambda m: [{"live": a, "case": b} for a, b in m]
    docs["fact_mapping"] = {"kind": "fact_mapping", "case": "REF1", "frame": dict(g.pair.frame.model_dump()),
        "note": "n", "options": dict(g.options_map), "matched": pm(fm["matched"]),
        "corresponding": [{**x, "note": "state differs"} for x in pm(fm["corresponding"])],
        "live_only": fm["live_only"], "case_only": fm["case_only"]}
    docs["consideration_enumeration"] = {"kind": "consideration_enumeration", "considerations": g.considerations_live()}
    cm = g.cons_map
    docs["consideration_mapping"] = {"kind": "consideration_mapping", "case": "REF1",
        "matched": [{**x, "role": "same role"} for x in pm(cm["matched"])],
        "corresponding": [{**x, "role": "similar role"} for x in pm(cm["corresponding"])],
        "live_only": cm["live_only"], "case_only": [{"case": c, "assumption": None} for c in cm["case_only"]]}
    docs["applicability"] = {"kind": "applicability", "case": "REF1", "frame": dict(g.pair.frame.model_dump()),
        "governs": g.pair.governs, "why": "The case rests on REF1-C1 and its condition recurs."}
    other = next(o for o in g.option_ids if o != g.choice)
    docs["reasoning"] = {"kind": "reasoning", "case": "REF1", "case_approach": "REF1 weighed lives first.",
        "weighing": "Weighing by the case's conditions" + (f" ({g.via[0]} fired)." if g.via else "."),
        "tradecraft": "Act carefully.", "uncertainty": "Estimates may be off.", "handoff": "I decide.",
        "tempting_wrong": {"option": other, "pull": "It looks safe.", "why_wrong": "It is too late."},
        "rejected": {other: "Set aside."}}
    docs["verdict"] = {"kind": "verdict", "choice": g.choice, "course": "Do the chosen thing.",
        "relation": g.pair.relation, "via": list(g.via) or None, "decisive": g.decisive, "now": ["Step one."],
        "flip_conditions": g.flips_live()}
    if not g.pair.governs:
        docs.pop("reasoning")
    if mutate:
        mutate(docs)
    return "\n---\n".join(yaml.safe_dump(d, sort_keys=False, allow_unicode=True, width=200) for d in docs.values())
