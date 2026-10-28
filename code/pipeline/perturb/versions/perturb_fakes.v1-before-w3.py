"""Offline stand-in for bench.models.complete used by the perturb and pair tests."""
from __future__ import annotations

import json
import re
from pathlib import Path

from pipeline.perturb.common import pilot_scenario

ROOT = Path(__file__).resolve().parents[4]
CASES = ROOT / "data" / "cases"


def pilot(case_id: str, split="eval-only"):
    fam = case_id.split("@")[0][3:].rsplit("-r", 1)[0]
    return pilot_scenario(CASES / fam / f"{case_id}.case.yaml", split)


def scr(t: str) -> str:
    """Change every plain word (refs like {F3} and ids are left alone)."""
    return re.sub(r"\b[A-Za-z]{3,}\b", lambda m: m.group(0) + "x", t)


def block(user: str, marker: str) -> dict:
    i = user.index(marker) + len(marker)
    return json.JSONDecoder().raw_decode(user[user.index("{", i):])[0]


class Fake:
    def __init__(self, realize=None, solver_choice="O1", propose=None, touched="C3", verify=True):
        self.realize = list(realize or [])
        self.solver_choice = solver_choice
        self.propose = propose or {"kind": "situation", "status": "confirmed",
                                   "text": "A relief tug is reportedly forty minutes away on a heading that avoids the strait.",
                                   "bears_on": "none"}
        self.touched, self.verify = touched, verify
        self.calls: list[tuple[str, list[dict]]] = []

    def __call__(self, role, messages, **kw):
        self.calls.append((role, messages))
        sysm, user = messages[0]["content"], messages[1]["content"]
        if "make ONE listed condition true" in sysm:
            return json.dumps(self.realize.pop(0) if len(self.realize) > 1 else self.realize[0])
        if "You check a claim" in sysm:
            return json.dumps({"holds": self.verify, "why": "stub"})
        if "Propose ONE additional fact" in sysm:
            return json.dumps(self.propose)
        if "expert decision analyst" in sysm:
            facts = re.findall(r"^(F\d+) ", user, re.M)
            return json.dumps({"choice": self.solver_choice, "considerations": [
                {"facts": facts[:2], "equity": "x_interest", "favors": [self.solver_choice], "weight": "strong", "why": "stub"}],
                "reasoning": "stub", "flip": "stub"})
        if "You rewrite decision scenarios" in sysm:
            return json.dumps(self.rewrite(user))
        raise AssertionError("unknown prompt")

    # --- rewrite: restyle / flip compose / add_fact restyle_fq / add_fact compose
    def rewrite(self, user):
        task = user.split("\n", 1)[0]
        if "TASK (restyle F and Q)" in task:
            b = block(user, "BUNDLE:")
            return self.fq(b)
        if "TASK (compose the answer)" in task:
            return self.answer(block(user, "PARENT ANSWER"), block(user, "SCENARIO FACTS AND FRAME"), user)
        b = block(user, "BUNDLE:")
        out = self.fq(b)
        if "TASK (flip)" in task:
            m = re.search(r"best decision is now (\S+) ", task + user)
            then = re.search(r"best decision is now (O\d+)", user).group(1)
            fired = re.search(r"Item (flip\d+) must now read", user).group(1)
            out.update(self.answer_parts(b, then, fired))
        else:                                   # restyle
            out.update(self.answer_parts(b, None, None))
        return out

    def fq(self, b):
        out = {k: scr(b[k]) for k in ("setting", "decider", "agent", "situation", "question")}
        out["options"] = {k: scr(v) for k, v in b["options"].items()}
        out["facts"] = {k: (v["text"] if isinstance(v, dict) else (v + " (as reported)" if v == self.propose["text"] else scr(v))) for k, v in b["facts"].items()}
        return out

    def answer_parts(self, b, then, fired):
        cons = {}
        for cid, c in b["considerations"].items():
            cons[cid] = {"why": scr(c["why"])}
        out = {"considerations": cons}
        r = b["reasoning"]
        out["reasoning"] = {k: scr(r[k]) for k in ("read", "weighing", "tradecraft", "uncertainty", "handoff")}
        out["reasoning"]["tempting_wrong"] = {"pull": scr(r["tempting_wrong"]["pull"]), "why_wrong": scr(r["tempting_wrong"]["why_wrong"])}
        out["reasoning"]["rejected"] = {k: scr(v) for k, v in r["rejected"].items()}
        out["flip"] = {}
        for k, v in b["flip"].items():
            out["flip"][k] = {kk: scr(vv) for kk, vv in v.items() if kk in ("if", "what", "why")}
        out["lesson"], out["limits"] = scr(b["lesson"]), scr(b["limits"])
        if then:
            tc = self.touched
            cons[tc] = {"why": scr(b["considerations"][tc]["why"]), "facts": b["considerations"][tc]["facts"],
                        "favors": [then], "weight": "weak"}
            # decisive: some consideration that favors `then`
            fav = [c for c, v in b["considerations"].items() if then in v["favors"]] or [tc]
            out["decisive"] = fav[:1]
            other = [o for o in b["verdict"] and ["O1", "O2"] if o != then][0]
            out["reasoning"]["tempting_wrong"]["option"] = other
            out["reasoning"]["rejected"] = {other: "stub rejected"}
            out["flip"][fired]["if"] = "stub reversal condition"
        else:
            out["decisive"] = b["verdict"]["decisive"]
        return out

    def answer(self, parent, fq, user):
        choice = re.search(r"analyst[^\n]*chose (O\d+)", user).group(1)
        out = self.answer_parts(parent, None, None)
        pc = parent["verdict"]["choice"]
        out["decisive"] = [c for c, v in parent["considerations"].items() if choice in v["favors"]][:1] or [
            "NEW"]
        if out["decisive"] == ["NEW"]:
            out["new_considerations"] = [{"facts": ["F1"], "equity": "new_interest", "favors": [choice], "weight": "strong", "why": "stub"}]
            out["decisive"] = [f"C{max(int(c[1:]) for c in parent['considerations']) + 1}"]
        other = [o for o in ("O1", "O2") if o != choice][0]
        out["reasoning"]["tempting_wrong"]["option"] = other
        out["reasoning"]["rejected"] = {other: "stub rejected"}
        if choice != pc:
            out["new_would_change"] = [{"if": "stub condition restoring the parent verdict", "then": pc, "why": "stub"}]
        out["touches"] = {"consideration": self.touched, "condition": "the parent's weighing of the module", "how": "bears on it"}
        return out
