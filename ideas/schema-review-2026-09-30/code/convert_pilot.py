"""Convert the DOHA/FISC pilot (src/data-scaling-v1/pilot-unzipped/pilot) to v7 catalogs and records.

Writes catalogs/SEC-F.yaml, catalogs/FISC.yaml, records/DOHA-F-01..10.yaml, records/FISC-01..03.yaml.
Programmatic and lossless where v7 has a slot; everything else is kept under provenance.conversion
or guidance.teaching. Run: python3 convert_pilot.py"""
import glob, os, re, yaml

HERE = os.path.dirname(os.path.abspath(__file__))
PILOT = os.path.abspath(os.path.join(HERE, "../src/data-scaling-v1/pilot-unzipped/pilot"))
STAKES = {"T0": {"L": 1, "k": 0.2}, "T1": {"L": 3, "k": 0.3}, "T2": {"L": 5, "k": 0.4},
          "T3": {"L": 9, "k": 0.5}, "T4": {"L": 19, "k": 0.5}}
ROLES = {"none": None, "recommend": None, "execute": "agent", "decide": "agent"}


def eqmap(pairs):
    return {e: s for e, s in pairs}


def dump(obj, path, header):
    with open(path, "w") as fh:
        fh.write(header)
        yaml.safe_dump(obj, fh, sort_keys=False, width=110, allow_unicode=True)


def secf_catalog():
    c = yaml.safe_load(open(f"{PILOT}/catalog-F.yaml"))["catalog"]
    f = {}
    for fid, v in c["factors_B"].items():
        f[fid] = {"issue": "ELIG", "favors": "B", "text": v["text"], "para": v["para"], "equities": eqmap(v["equities"])}
        if v.get("forced_significance"):
            f[fid]["knockout"] = True                     # pilot: forced_significance
            if v.get("why_forced"):
                f[fid]["why_knockout"] = v["why_forced"]
        f[fid]["author"] = v.get("author", "draft")
    for fid, v in c["factors_A"].items():
        if "scale" in v:                                 # A20d: rungs initiated < established
            rungs = {k: eqmap(s["equities"]) for k, s in v["scale"].items()}
            top = list(rungs)[-1]
            f[fid] = {"issue": "ELIG", "favors": "A", "text": v["text"], "para": v["para"], "equities": rungs[top],
                      "dimension": "remediation", "rungs": rungs,
                      "rung_means": {k: s["means"] for k, s in v["scale"].items()}, "author": v.get("author", "draft")}
        else:
            f[fid] = {"issue": "ELIG", "favors": "A", "text": v["text"], "para": v["para"],
                      "equities": eqmap(v["equities"]), "author": v.get("author", "draft")}
    for fid, v in c["factors_doctrine"].items():          # behind a flag (pilot run 2)
        f[fid] = {"issue": "ELIG", "favors": v["favors"], "text": v["means"], "equities": eqmap(v["equities"]),
                  "flag": "doctrine", "source": v["source"], "author": v.get("author", "draft")}
    return {"catalog": {
        "id": "SEC-F", "version": "2026-09-29", "sub_area": c["sub_area"], "source": c["source"],
        "concern": c["concern"],
        "issues": {"ELIG": {"question": "Grant or continue national security eligibility?",
                            "sides": {"A": "favorable", "B": "unfavorable"},
                            "means": {k: v["means"] for k, v in c["options"].items()},
                            "action": {"A": "GRANT_ELIGIBILITY", "B": "DENY_ELIGIBILITY"},
                            "default": c["default"]["outcome"], "default_quotes": c["default"]["quotes"]}},
        "equities": {k: {"text": v["rationale"], "author": v.get("author", "draft")} for k, v in c["equities"].items()},
        "dimensions": {"remediation": ["initiated", "established"]},
        "factors": f,
        "conditions": {},
        "actions": {"GRANT_ELIGIBILITY": {"direction": "permissive", "reversible": True, "tier": "T2"},
                    "DENY_ELIGIBILITY": {"direction": "permissive", "reversible": True, "tier": "T2",
                                         "note": "r2 adaptation: an adverse eligibility determination is a decision against a person, "
                                                 "not a status-quo hold; v2 makes restrictive sides within any role, so a restrictive DENY "
                                                 "would let a recommend-role agent deny autonomously and 'hold' it as an interim atom"}},
        "authority": {"levels": ["agent", "analyst", "administrative_judge", "appeal_board", "agency_head"],
                      "tiers": {"T0": "agent", "T1": "analyst", "T2": "administrative_judge", "T3": "appeal_board",
                                "T4": "agency_head"},
                      "roles": ROLES, "tier_floors": {}, "non_delegable_to_agent": [], "inherent": []},
        "stakes": STAKES, "coupling": [], "tagging_rules": c["tagging_rules"]}}


def fisc_catalog():
    c = yaml.safe_load(open(f"{PILOT}/catalog-FISC-702q.yaml"))["catalog"]
    f = {}
    for fid, v in c["factors"].items():
        f[fid] = {"issue": "QRY", "favors": v["favors"], "text": v["means"], "equities": eqmap(v["equities"])}
        if v.get("author"):
            f[fid]["author"] = v["author"]
    return {"catalog": {
        "id": c["id"], "version": "2026-09-29", "standard": c["standard"],
        "issues": {"QRY": {"question": "Run this query against raw Section 702 information?",
                           "sides": {"A": "run", "B": "do_not_run"}, "means": c["options"],
                           "action": {"A": "RUN_RAW_702_QUERY", "B": "DO_NOT_QUERY"},
                           "default": c["default"]["outcome"], "default_basis": c["default"]["basis"]}},
        "equities": {k: {"text": v} for k, v in c["equities"].items()},
        "dimensions": {}, "factors": f, "conditions": {},
        "actions": {"RUN_RAW_702_QUERY": {"direction": "permissive", "reversible": False, "tier": "T0"},
                    "DO_NOT_QUERY": {"direction": "restrictive", "reversible": True}},
        "authority": {"levels": ["agent", "supervisor", "attorney", "nsd", "fisc"],
                      "tiers": {"T0": "agent", "T1": "supervisor", "T2": "attorney", "T3": "nsd", "T4": "fisc"},
                      "roles": ROLES, "tier_floors": {}, "non_delegable_to_agent": [], "inherent": []},
        "stakes": STAKES, "coupling": []}}


def close_tags(tags, scaled):
    out = list(tags)
    for stem, ladder in scaled.items():
        for i, t in enumerate(ladder):
            if t in out:
                out += [x for x in ladder[:i] if x not in out]
    return out


FLIP = re.compile(r"^\s*([+-])([A-Za-z0-9@]+)")


def typed_flips(case, known, tags=()):
    """Pilot flip_rules -> v7 typed flips when the rule keys on one catalog tag and is not unit-scoped;
    the rest stay as untyped teaching notes."""
    typed, untyped = [], []
    for i, fr in enumerate(case.get("flip_rules") or []):
        m = FLIP.match(fr["if"])
        then = str(fr["then"])
        out = re.match(r"^([AB])\b", then)
        noop = m and m.group(1) == "+" and m.group(2) in tags
        if noop:
            untyped.append(dict(fr, demoted="change is a no-op on this record's tags (Horty lint: it would bind "
                                              "against the base holding); the catalog cannot express 'new' B19a"))
        elif m and m.group(2) in known and out and fr.get("scope") not in ("allegation", "identifier"):
            fl = {"id": f"x{i + 1}", "event": "world", "change": {("add" if m.group(1) == "+" else "remove"): [m.group(2)]},
                  "then": {"issue": case["_issue"], "outcome": out.group(1),
                           "force": "permitted" if "hedged" in then else "required"},
                  "why": fr.get("basis", "")}
            if fr.get("scope"):
                fl["scope"] = fr["scope"]
            typed.append(fl)
        else:
            untyped.append(fr)
    return typed, untyped


def fact(g, scaled, status_default):
    st = g.get("status", status_default)
    status = {"claimed": "reported", "FBI argument, rejected": "rejected"}.get(st, st)
    f = {"id": g["id"], "text": g["text"], "status": status, "channel": "record",
         "tags": close_tags(g.get("factors") or [], scaled)}
    if g.get("credibility") == "rejected":
        f["credibility"] = "discredited"
    notes = [n for n in (g.get("note"), "doctrine-extension tag" if g.get("extension") else None,
                         f"pilot status: {st}" if st != status else None) if n]
    if notes:
        f["note"] = "; ".join(notes)
    return f


def doha_record(path, known, scaled):
    d = yaml.safe_load(open(path))
    c, conv = d["case"], d["conversion"]
    c["_issue"] = "ELIG"
    judge = "DOHA administrative judge"
    flips, untyped = typed_flips(c, known, {t for g in c["facts"] for t in g.get("factors") or []})
    src = c["source"]
    return {"record": {
        "id": c["id"], "title": src["caseno"], "catalog": "SEC-F@2026-09-29",
        "provenance": {"kind": "adjudicated", "gold_kind": "ruling", "seed": src["caseno"], "source": src,
                       "authority": {"source": judge, "rank": 1, "status": "current", "date": str(src["date"])},
                       "decided_by": c["decided_by"],
                       "conversion": {"from": f"pilot/cases/{os.path.basename(path)}", "split": conv["split"],
                                      "minutes": conv.get("minutes"), "misfits": conv.get("misfits") or [],
                                      "perception": "judge (tags follow the judge's findings; P1 leak for held-out use)"}},
        "units": [],
        "situation": {
            "agent": {"role": c.get("agent_role", "recommend"), "serves": judge},
            "facts": [fact(g, scaled, "found") for g in c["facts"]],
            "authority": {"deciders": [{"holder": judge, "holds": ["GRANT_ELIGIBILITY", "DENY_ELIGIBILITY"]}],
                          "delegations": [], "orders": []},
            "options": [{"text": v, "plan": [{"act": "proceed", "issue": "ELIG", "side": k}]}
                        for k, v in c["options"].items()]},
        "resolution": {
            "holdings": [{"issue": "ELIG", "outcome": c["outcome"], "reason": list(c["reason"]), "force": "required"}],
            "routed": [{"issue": "ELIG", "side": c["outcome"], "because": "authorize", "to": [judge]}],
            "plan": [{"act": "route", "issue": "ELIG", "side": c["outcome"], "because": "authorize", "to": [judge],
                      "recommend": c["outcome"]}],
            "status": "settled", "holding_text": c["holding"].strip(), "reason_cite": c.get("reason_cite")},
        "guidance": {"flips": flips, "anomaly_cues": [],
                     "teaching": {"watch_for_v6": c.get("watch_for") or [], "untyped_flips": untyped}},
        "review": None}}


def fisc_record(path, known):
    d = yaml.safe_load(open(path))
    c = d["case"]
    c["_issue"] = "QRY"
    querier = "FBI querier"
    src = c["source"]
    units, holdings, facts = [], [], []
    for g in c["facts"]:
        f = fact(g, {}, "found")
        if g.get("scope"):
            f["about"] = ["u8"]
        facts.append(f)
    if isinstance(c["outcome"], dict):                   # FISC-02: per-identifier outcomes
        units = [{"id": "u8", "class": "identifier", "text": "the eight identifiers NSD found tied to foreign-influence activity"},
                 {"id": "urest", "class": "identifier", "text": "the remaining donor identifiers (over 19,000 in the batch)"}]
        holdings = [{"issue": "QRY", "units": ["u8"], "outcome": "A", "reason": c["reason"]["A"], "force": "required"},
                    {"issue": "QRY", "units": ["urest"], "outcome": "B", "reason": c["reason"]["B"], "force": "required"}]
        plan = [{"act": "proceed", "issue": "QRY", "side": "A", "units": ["u8"]},
                {"act": "proceed", "issue": "QRY", "side": "B", "units": ["urest"]}]
    else:
        holdings = [{"issue": "QRY", "outcome": c["outcome"], "reason": list(c["reason"]), "force": "required"}]
        plan = [{"act": "proceed", "issue": "QRY", "side": c["outcome"]}]
    flips, untyped = typed_flips(c, known) if not units else ([], c.get("flip_rules") or [])
    return {"record": {
        "id": c["id"], "title": f"{src['doc']}, p. {src['page']}", "catalog": "INT-702Q@2026-09-29",
        "provenance": {"kind": "investigated", "gold_kind": "review_finding", "seed": f"FISC opinion p. {src['page']}",
                       "source": src,
                       "authority": {"source": c["decided_by"], "rank": 2, "status": "current", "date": "2022-04-21"},
                       "decided_by": c["decided_by"],
                       "conversion": {"from": f"pilot/cases/{os.path.basename(path)}",
                                      "misfits": (d.get("conversion") or {}).get("misfits") or []}},
        "units": units,
        "situation": {
            "agent": {"role": c.get("agent_role", "execute"), "serves": "FBI case agent"},
            "facts": facts,
            "authority": {"deciders": [{"holder": querier, "holds": ["RUN_RAW_702_QUERY"]}],
                          "delegations": [], "orders": []},
            "options": [{"text": v, "plan": [{"act": "proceed", "issue": "QRY", "side": k}]}
                        for k, v in c["options"].items()]},
        "resolution": {"holdings": holdings, "routed": [], "plan": plan, "status": "settled",
                       "holding_text": c["holding"].strip(), "reason_cite": c.get("reason_cite")},
        "guidance": {"flips": flips, "anomaly_cues": [],
                     "teaching": {"watch_for_v6": c.get("watch_for") or [], "untyped_flips": untyped}},
        "review": {"body": c["decided_by"], "standard": "FBI Querying Procedures § IV.A.1 (as quoted in the Opinion, p. 35)",
                   "decision_assessment": "unacceptable", "result": "unknown", "failure_mode": None,
                   "findings": [{"id": "n1", "text": c["holding"].strip(), "evidence": c.get("reason_cite")}]}}}


def main():
    sec, fisc = secf_catalog(), fisc_catalog()
    hdr = "# Generated by convert_pilot.py from the DOHA/FISC pilot. Do not hand-edit; edit the converter.\n"
    dump(sec, f"{HERE}/catalogs/SEC-F.yaml", hdr + "# SEC-F (SEAD 4 Guideline F): one binary issue ELIG, A favorable / B unfavorable, default B.\n"
         "# A20d is a two-rung scale (initiated < established); doctrine factors BX1, BX2, AX1 sit behind flag: doctrine.\n")
    dump(fisc, f"{HERE}/catalogs/FISC.yaml", hdr + "# INT-702Q (FISC 702 querying): one binary issue QRY, A run / B do not run, default B.\n")
    known = set(sec["catalog"]["factors"])
    scaled = {"A20d": ["A20d@initiated", "A20d@established"]}
    known |= set(scaled["A20d"])
    for p in sorted(glob.glob(f"{PILOT}/cases/DOHA-F-*.yaml")):
        r = doha_record(p, known, scaled)
        dump(r, f"{HERE}/records/{r['record']['id']}.yaml", hdr)
    fk = set(fisc["catalog"]["factors"])
    for p in sorted(glob.glob(f"{PILOT}/cases/FISC-*.yaml")):
        r = fisc_record(p, fk)
        dump(r, f"{HERE}/records/{r['record']['id']}.yaml", hdr)
    print("wrote catalogs/SEC-F.yaml, catalogs/FISC.yaml, 10 DOHA and 3 FISC records")


if __name__ == "__main__":
    main()
