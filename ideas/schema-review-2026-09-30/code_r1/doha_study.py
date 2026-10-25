"""DOHA Guideline F pilot rerun: solver_v2 (via the pilot's own run_heldout loaders) vs solver_v3 (v7 records).

Leave-one-out over all 10 cases; for every single-tag add/remove (with closure; the red team's 20 x 10
perturbation set) count action changes and wrong autonomous acts; baselines (count of A-side tags, 1-NN,
always-deny). Writes results/doha-v3.md.  Run: python3 doha_study.py

Harness action, both solvers: act on the settled side, else ask/route (no pi: the study isolates
precedent logic, as rt_doha.py did). For v3 the agent gets a study delegation for both classes so the
authority gate never intervenes; under the records' real role (recommend) every item routes."""
import collections, io, os, sys
sys.dont_write_bytecode = True        # never write caches under src/ (read-only inputs)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "src/schema"))                       # solver_v2 (unmodified)
sys.path.insert(1, os.path.join(ROOT, "src/data-scaling-v1/pilot-unzipped/pilot"))
sys.path.insert(0, HERE)
import solver_v2 as V2                                                      # noqa: E402
import run_heldout as RH                                                    # noqa: E402  (pilot loaders)
import solver_v3 as S                                                       # noqa: E402

IDS = [f"DOHA-F-{i:02d}" for i in range(1, 11)]
STUDY = {"deciders": [{"holder": "DOHA administrative judge", "holds": ["GRANT_ELIGIBILITY", "DENY_ELIGIBILITY"]}],
         "delegations": [{"to": "agent", "holds": ["GRANT_ELIGIBILITY", "DENY_ELIGIBILITY"], "when": [],
                          "source": "study device"}], "orders": []}
NAMES = {"A": "grant", "B": "deny", "ask": "ask"}


# ------------------------------------------------------------------------------------------------ v2
def v2_setup(doctrine):
    cat, _ = RH.load_catalog(doctrine)
    return cat, RH.load_cases(cat)


def v2_close(Y):
    Y = set(Y)
    if "A20d@established" in Y:
        Y.add("A20d@initiated")
    return Y


def v2_act(cat, cb, Y):
    lvl, out, res = V2.support(cat, cb, Y)
    return (out if lvl in ("binding", "analogous") else "ask"), lvl, \
        sorted(k for k, (lab, _) in res.items() if lab in ("binding", "analogous"))


def v2_perturb(cat, Y0):
    for f in sorted(cat):
        if f not in Y0:
            yield "+" + f, v2_close(Y0 | {f})
        elif f != "A20d@initiated":
            yield "-" + f, v2_close(Y0 - {f})
        else:
            yield "-" + f, Y0 - {"A20d@initiated", "A20d@established"}


# ------------------------------------------------------------------------------------------------ v3
def v3_setup(doctrine, flips=False):
    cat = S.load_catalog(os.path.join(HERE, "catalogs/SEC-F.yaml"), ("doctrine",) if doctrine else ())
    recs = {i: S.load_yaml(os.path.join(HERE, f"records/{i}.yaml")) for i in IDS}
    cards = {i: S.cards_from_record(cat, recs[i], with_flips=flips) for i in IDS}
    sits = {i: S.situation_from_record(cat, recs[i]) for i in IDS}
    real = {i: recs[i]["record"]["resolution"]["holdings"][0]["outcome"] for i in IDS}
    return cat, cards, sits, real


def v3_act(cat, cards, sit, tags):
    s = dict(sit, tags=set(tags), authority=STUDY)
    a = S.compose(cat, cards, s, issues=["ELIG"])
    act, ass = a["actions"]["ELIG"], a["assessed"]["ELIG"]
    binders = sorted(k[0] for k, v in ass["verdicts"].items() if v.get("verdict") in S.FORCING)
    status = ass["label"] or ass["status"]
    return (act["side"] if act["act"] == "proceed" else "ask"), status, binders


# ------------------------------------------------------------------------------------------------ study
def loo(kind, doctrine=False, flips=False):
    rows, tally = [], collections.Counter()
    ex = []
    if kind == "v2":
        cat, cases = v2_setup(doctrine)
        real = {i: cases[i]["outcome"] for i in IDS}
        tags = {i: cases[i]["facts"] for i in IDS}
        act = lambda h, Y: v2_act(cat, {k: v for k, v in cases.items() if k != h}, Y)
        pert = lambda h: v2_perturb(cat, tags[h])
    else:
        cat, cards, sits, real = v3_setup(doctrine, flips)
        tags = {i: sits[i]["tags"] for i in IDS}
        act = lambda h, Y: v3_act(cat, [c for k in IDS if k != h for c in cards[k]], sits[h], Y)
        v2cat, _ = v2_setup(doctrine)
        pert = lambda h: ((ch, S.apply_change(cat, tags[h], [ch])) for ch in
                          (("+" if f not in tags[h] else "-") + f for f in sorted(v2cat)))
    for h in IDS:
        a0, lvl, binders = act(h, tags[h])
        changed = wrong = 0
        for name, Y in pert(h):
            a, _, _ = act(h, Y)
            tally["probes"] += 1
            if a != a0:
                changed += 1
                k = ("ask->act(right)" if a == real[h] else "ask->act(WRONG)") if a0 == "ask" else \
                    ("act->ask" if a == "ask" else "act->act(flipped)")
                tally[k] += 1
                if a not in ("ask", real[h]):
                    wrong += 1
                    ex.append(f"{h} ({NAMES[real[h]]}) {name}: {NAMES[a0]} -> {NAMES[a]}")
        tally["changed"] += changed
        tally["wrong"] += wrong
        tally["decided"] += a0 != "ask"
        tally["correct"] += a0 == real[h]
        rows.append((h, real[h], lvl, a0, binders, changed))
    return rows, tally, ex, tags, real


def baselines(tags, real, side):
    nA = {h: sum(side(t) == "A" for t in tags[h]) for h in IDS}
    nB = {h: sum(side(t) == "B" for t in tags[h]) for h in IDS}
    out = {"always deny (SEAD 4 default B)": sum(real[h] == "B" for h in IDS),
           "count of A-side tags: grant iff #A >= 4": sum(("A" if nA[h] >= 4 else "B") == real[h] for h in IDS),
           "count of A-side tags: #A - #B >= 2": sum(("A" if nA[h] - nB[h] >= 2 else "B") == real[h] for h in IDS)}
    hits = 0
    for h in IDS:
        tr = [k for k in IDS if k != h]
        best = max(range(0, 8), key=lambda t: (sum((("A" if nA[k] >= t else "B") == real[k]) for k in tr), -t))
        hits += ("A" if nA[h] >= best else "B") == real[h]
    out["count of A-side tags, threshold chosen leave-one-out"] = hits
    jac = lambda a, b: len(a & b) / len(a | b) if a | b else 0
    nn = 0
    for h in IDS:
        k = max((k for k in IDS if k != h), key=lambda k: (jac(tags[k], tags[h]), k))
        nn += real[k] == real[h]
    out["1-NN (Jaccard on tags, leave-one-out)"] = nn
    return out


def split_6_4(kind):
    """The pilot's original split: casebook F-01, 02, 05, 06, 09, 10; held out F-03, 04, 07, 08."""
    cb_ids = ["DOHA-F-01", "DOHA-F-02", "DOHA-F-05", "DOHA-F-06", "DOHA-F-09", "DOHA-F-10"]
    out = {}
    if kind == "v2":
        cat, cases = v2_setup(False)
        for h in ("DOHA-F-03", "DOHA-F-04", "DOHA-F-07", "DOHA-F-08"):
            out[h] = v2_act(cat, {k: cases[k] for k in cb_ids}, cases[h]["facts"])[:2]
    else:
        cat, cards, sits, real = v3_setup(False)
        for h in ("DOHA-F-03", "DOHA-F-04", "DOHA-F-07", "DOHA-F-08"):
            out[h] = v3_act(cat, [c for k in cb_ids for c in cards[k]], sits[h], sits[h]["tags"])[:2]
    return out


INTERPRETATION = """
## Where v3 is better, worse, or the same

**Better: wrong autonomous acts under one-tag noise are halved (4 -> 2 of 200; 3 -> 1 of 230 with the
doctrine factors).** The two v2 wrong grants that came from any-equity downplay are gone: DOHA-F-07 + A20b2
and DOHA-F-10 + A20b2 ("acted responsibly" standing in for actual repayment). Per-equity significance
leaves `current_burden` uncovered, so DOHA-F-01 no longer governs. One of v2's two act -> act flips
(DOHA-F-07 + A20b2) is among them.

**Same: the two wrong grants that remain are not a solver defect.** Both add `A20d@established`
(documented, sustained repayment) to a denial with no repayment. That tag *is* DOHA-F-01's dispositive
mitigator, so the grant precedent now binds a fortiori. v3 treats the tag as true, as it must; the defence
is perception (record-perception tags, the action-margin stratification the red team proposed, or a
perception-confidence field), not precedent logic.

**Worse: coverage drops from 4/10 to 3/10 decided by precedent** (5/10 -> 3/10 with doctrine). The lost
item is DOHA-F-04, which v2 granted "analogous" only because any-equity downplay let `responsible_conduct`
cover a missing `A20d@established` while nothing covered `current_burden`. That is exactly the M2 pattern,
so the loss is the price of the fix, as the red team predicted (per-equity patch: 3/10). With doctrine,
v2 also decided DOHA-F-10 (analogous via DOHA-F-07); v3 leaves it bounded because spec 3.2 scores a
new-against distinction at its catalog strength, so F-10's weak A20c1 and A20d@initiated count even though
the strong BX1/B19a block them in F-10 (effective strength 0; v2 skipped such equities). REPORT.md
amendment A5 would restore that decision (see the switch `NEW_AGAINST_EFFECTIVE`). Accuracy on decided
items is 100% for both solvers.

**Roughly the same: one-tag sensitivity of the action** (33 -> 31 of 200). Most changes are still
act -> ask on the three decided items (22 of 31), i.e. the conservative direction. The decided items are
fragile to one edit (DOHA-F-05 8/20, F-07 9/20, F-08 6/20), so the action-margin stratification remains
necessary.

**Unchanged and still decisive against both solvers: the baselines.** On judge-perception tags a count of
A-side tags gets 10/10 (9/10 with the threshold chosen leave-one-out) and 1-NN (Jaccard, leave-one-out)
gets 8/10, against 3/10 decided (all correct) for v3. This is circularity in the tags (the judge's findings
encode the verdict), not evidence about the solver; only record-perception tags can separate them
(pilot recommendation 2).

**Consistency.** The DOHA casebook is Horty-consistent under v3 (0 opposite-outcome pairs forcing on the
union of their reasons, with and without doctrine). Compiling the pilot's flip rules exposed one authoring
defect: DOHA-F-05's "+B19a (new delinquencies) -> deny" is a no-op on a record that already has B19a, so
its near-miss card binds against the base holding (naqd lint). The converter demotes it to an untyped note.
"""


def main():
    out = io.StringIO()
    w = lambda s="": out.write(s + "\n")
    w("# DOHA Guideline F pilot, rerun: solver_v2 vs solver_v3 (v7)")
    w()
    w("Generated by `code/doha_study.py` (2026-09-29). solver_v2 runs through the pilot's own `run_heldout.py`")
    w("loaders on `catalog-F.yaml` and the pilot case files; solver_v3 runs on `catalogs/SEC-F.yaml` and the")
    w("converted `records/DOHA-F-*.yaml`. Tags are judge-perception (the converter's reading of the findings).")
    w("Harness action for both: act on the settled side, otherwise ask/route; no model distribution is used,")
    w("so the study isolates precedent logic (as `review/redteam/rt_doha.py` did). For v3 the agent is given a")
    w("study delegation for both classes so the authority gate does not intervene; under the records' real")
    w("role (`recommend`), v3 routes every item to the judge with the settled side as its recommendation.")
    w()
    res = {k: loo(k) for k in ("v2", "v3")}
    resd = {k: loo(k, doctrine=True) for k in ("v2", "v3")}
    w("## Headline (SEAD 4 catalog; leave-one-out over all 10)")
    w()
    w("| Solver | Decided by precedent | Correct when decided | One-tag perturbations that change the action | ...that produce a wrong autonomous act |")
    w("|---|---|---|---|---|")
    for k in ("v2", "v3"):
        t = res[k][1]
        w(f"| solver_{k} | {t['decided']}/10 | {t['correct']}/{t['decided']} | {t['changed']}/{t['probes']} | {t['wrong']}/{t['probes']} |")
    for k in ("v2", "v3"):
        t = resd[k][1]
        w(f"| solver_{k} + doctrine (BX1, BX2, AX1) | {t['decided']}/10 | {t['correct']}/{t['decided']} | {t['changed']}/{t['probes']} | {t['wrong']}/{t['probes']} |")
    w()
    w("Red-team reference (`rt_doha_fix.py`): solver_v2 4/10, 33/200, 4/200; per-equity patch 3/10, 28/200, 2/200.")
    w()
    w("## Per case (leave-one-out, SEAD 4 catalog)")
    w()
    w("| Case | Real | v2 support | v2 action | v3 support | v3 action | v3 forcing precedents | one-tag changes v2 / v3 |")
    w("|---|---|---|---|---|---|---|---|")
    for r2, r3 in zip(res["v2"][0], res["v3"][0]):
        w(f"| {r2[0]} | {NAMES[r2[1]]} | {r2[2]} | {NAMES[r2[3]]} | {r3[2]} | {NAMES[r3[3]]} | "
          f"{', '.join(r3[4]) or '-'} | {r2[5]}/20 / {r3[5]}/20 |")
    w()
    w("## Kinds of action change under one-tag perturbation")
    w()
    w("| Solver | act -> ask | ask -> act (right) | ask -> act (WRONG) | act -> act (flipped) |")
    w("|---|---|---|---|---|")
    for k in ("v2", "v3"):
        t = res[k][1]
        w(f"| solver_{k} | {t['act->ask']} | {t['ask->act(right)']} | {t['ask->act(WRONG)']} | {t['act->act(flipped)']} |")
    w()
    for k in ("v2", "v3"):
        w(f"Wrong autonomous acts, solver_{k}: " + ("; ".join(res[k][2]) or "none"))
        w()
    w("## Baselines (same tags, same 10 cases)")
    w()
    cat3 = S.load_catalog(os.path.join(HERE, "catalogs/SEC-F.yaml"))
    b = baselines(res["v3"][3], res["v3"][4], lambda t: cat3.side(t) if t in cat3.tag else None)
    w("| Rule | Correct |")
    w("|---|---|")
    for name, n in b.items():
        w(f"| {name} | {n}/10 |")
    w(f"| solver_v2, decided by precedent (rest ask) | {res['v2'][1]['correct']}/10 correct, {10 - res['v2'][1]['decided']} ask |")
    w(f"| solver_v3, decided by precedent (rest route) | {res['v3'][1]['correct']}/10 correct, {10 - res['v3'][1]['decided']} route |")
    w()
    w("## The pilot's original 6/4 split")
    w()
    s2, s3 = split_6_4("v2"), split_6_4("v3")
    real = res["v3"][4]
    w("| Held out | Real | v2 | v3 |")
    w("|---|---|---|---|")
    for h in s2:
        w(f"| {h} | {NAMES[real[h]]} | {s2[h][1]} -> {NAMES[s2[h][0]]} | {s3[h][1]} -> {NAMES[s3[h][0]]} |")
    w()
    fl = loo("v3", flips=True)[1]
    w(f"Serving the compiled flip cards as well (only DOHA-F-10/x1, `force: permitted`, survives conversion) "
      f"changes nothing: {fl['decided']}/10 decided, {fl['changed']}/{fl['probes']} changes, {fl['wrong']} wrong.")
    w(INTERPRETATION)
    with open(os.path.join(HERE, "results/doha-v3.md"), "w") as fh:
        fh.write(out.getvalue())
    print(out.getvalue())


if __name__ == "__main__":
    main()
