"""Round 2: run solver_v3 (spec v2 rules) on the six hand-converted Hard-Calls records (records/hc/, verbatim
copies of drafts/hc-v7-v2/). For each record: validate; gold round trip (served card = the record itself)
under four readings; run every typed flip. Returns data for results/r2-results.md (see r2_report.py).

Round-trip readings:  strict   = no pi (only precedent can settle; unsettled issues route)
                      hidden   = pi = one-hot hidden_resolution for unsettled issues (CHOICE; main reading)
                      literal  = hidden, but orders authorize without the level check (ORDER_LEVEL_CHECK off)
                      a5off    = hidden, A5 off (new-against distinctions at catalog strength, as spec v1)
Flips: apply the flip to the record (replace_fact, remove/add per unit, add_order; added tags carry the flip's
non-spec actor/form as by/form), serve the record's HOLDINGS only (not its compiled flips, which would bind
themselves), compose with no pi and with pi = the clause outcomes, and compare with each `then` clause."""
import glob, os, sys
import solver_v3 as S
import validate_v7 as V

HERE = os.path.dirname(os.path.abspath(__file__))
IDS = ["AUT-102", "AUT-103", "REL-105", "INT-109", "ANL-107", "AGT-106"]


def load(rid):
    rp = os.path.join(HERE, "records/hc", f"{rid}.yaml")
    r = S.load_yaml(rp)
    cid = r["record"]["catalog"].split("@")[0]
    cat = S.load_catalog(os.path.join(HERE, "catalogs/hc", f"catalog-{cid}.yaml"))
    return cat, r


def round_trip(cat, r, reading):
    old = (S.ORDER_LEVEL_CHECK, S.NEW_AGAINST_EFFECTIVE)
    S.ORDER_LEVEL_CHECK = reading != "literal"
    S.NEW_AGAINST_EFFECTIVE = reading != "a5off"
    try:
        cards = S.cards_from_record(cat, r)
        pi = None if reading == "strict" else V.hidden_pi(cat, r["record"])
        got = S.compose_record(cat, r, cards, pi)
        return S.plan_diff(r["record"]["resolution"]["plan"], got["plan"]), got
    finally:
        S.ORDER_LEVEL_CHECK, S.NEW_AGAINST_EFFECTIVE = old


def _action_for(got, issue, unit):
    return got["actions"].get((issue, unit) if unit else issue)


def run_flip(cat, r, fl):
    """-> list of clause results {clause, strict, with_pi, verdict}."""
    rr = S.apply_flip(cat, r, fl)
    cards = S.cards_from_record(cat, r, with_flips=False)
    clauses = S.as_list(fl["then"])
    pi = V.hidden_pi(cat, r["record"])
    for th in clauses:
        if th.get("outcome"):
            for u in S.as_list(th.get("units")) or [None]:
                pi[f"{th['issue']}[{u}]" if u else th["issue"]] = {s: float(s == th["outcome"]) for s in cat.sides(th["issue"])}
    outs = {"strict": S.compose_record(cat, rr, cards, None), "with_pi": S.compose_record(cat, rr, cards, pi)}
    routed_issues = {th["issue"] for th in clauses if th.get("route")}
    res = []
    for th in clauses:
        units = S.as_list(th.get("units")) or [None]
        if units == [None] and any(isinstance(key, tuple) and key[0] == th["issue"] for key in outs["strict"]["actions"]):
            units = [key[1] for key in outs["strict"]["actions"] if isinstance(key, tuple) and key[0] == th["issue"]]
        for u in units:
            row = {"clause": th, "unit": u}
            for k, got in outs.items():
                a = _action_for(got, th["issue"], u)
                if a is None:
                    row[k] = ("absent",)
                    continue
                if th.get("outcome"):
                    ok = a["act"] == "proceed" and a["side"] == th["outcome"] or \
                        (a["act"] == "route" and a.get("interim") == th["outcome"] and th["issue"] in routed_issues)
                else:
                    ok = a["act"] == "route" and a["because"] == th["route"]
                row[k] = (ok, S.action_key(a), a.get("because"), a.get("interim"), a.get("support"))
                if ok and th.get("to") and a["act"] == "route":
                    row[k + "_to"] = sorted(a["to"]) == sorted(S.as_list(th["to"]))
            # verdict: outcome clauses judged with pi = the clause outcome; route clauses without pi
            row["ok"] = bool(row["with_pi" if th.get("outcome") else "strict"][0] is True)
            row["ok_no_pi"] = bool(row["strict"][0] is True)
            row["to_ok"] = row.get(("with_pi" if th.get("outcome") else "strict") + "_to")
            res.append(row)
    return res, outs


def evaluate():
    out = {}
    for rid in IDS:
        cat, r = load(rid)
        vpath = [os.path.join(HERE, "records/hc", f"{rid}.yaml")] + sorted(glob.glob(os.path.join(HERE, "catalogs/hc/*.yaml")))
        nerr, rows = V.main(vpath, quiet=True)
        rec_row = next(x for x in rows if x[0].endswith(f"{rid}.yaml"))
        schema_lint_E = [e for e in rec_row[1] if not e.startswith("round trip")]
        rt = {k: round_trip(cat, r, k) for k in ("strict", "hidden", "literal", "a5off")}
        flips = {fl["id"]: run_flip(cat, r, fl)[0] for fl in r["record"]["guidance"]["flips"]}
        sit = S.situation_from_record(cat, r)
        out[rid] = {"lint_E": schema_lint_E, "lint_W": rec_row[2], "rt": rt, "flips": flips, "dropped": sit["dropped"],
                    "n_gold": len(S._atoms(r["record"]["resolution"]["plan"]))}
    return out


if __name__ == "__main__":
    res = evaluate()
    for rid, d in res.items():
        print(f"== {rid}: lint errors {d['lint_E']}; gold atoms {d['n_gold']}")
        for k, (diff, _) in d["rt"].items():
            print(f"   {k:8s} matched {len(diff['matched'])} missing {diff['missing']} extra {diff['extra']} attr {diff['attr']}")
        for fid, rows in d["flips"].items():
            for row in rows:
                th = {k: v for k, v in row["clause"].items() if k in ("issue", "outcome", "route", "units", "to")}
                print(f"   flip {fid} {th} unit={row['unit']}: OK={row['ok']} (no-pi {row['ok_no_pi']}) to={row['to_ok']} "
                      f"| strict {row['strict']} | pi {row['with_pi']}")
