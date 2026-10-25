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
import importlib.util                                                       # noqa: E402
_spec = importlib.util.spec_from_file_location("solver_r1", os.path.join(ROOT, "code_r1", "solver_v3.py"))
S1 = importlib.util.module_from_spec(_spec)                                 # round-1 solver (A5 off, v1 rules)
_spec.loader.exec_module(S1)
PACKS = {"v3-r1": (S1, os.path.join(ROOT, "code_r1")), "v3-r2": (S, HERE)}

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
def v3_setup(doctrine, flips=False, pack="v3-r2"):
    M, root = PACKS[pack]
    cat = M.load_catalog(os.path.join(root, "catalogs/SEC-F.yaml"), ("doctrine",) if doctrine else ())
    recs = {i: M.load_yaml(os.path.join(root, f"records/{i}.yaml")) for i in IDS}
    cards = {i: M.cards_from_record(cat, recs[i], with_flips=flips) for i in IDS}
    sits = {i: M.situation_from_record(cat, recs[i]) for i in IDS}
    real = {i: recs[i]["record"]["resolution"]["holdings"][0]["outcome"] for i in IDS}
    return cat, cards, sits, real


def v3_act(cat, cards, sit, tags, M=S):
    s = dict(sit, tags=set(tags), authority=STUDY)
    a = M.compose(cat, cards, s, issues=["ELIG"])
    act, ass = a["actions"]["ELIG"], a["assessed"]["ELIG"]
    binders = sorted(k[0] for k, v in ass["verdicts"].items() if v.get("verdict") in M.FORCING)
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
        M = PACKS[kind][0]
        cat, cards, sits, real = v3_setup(doctrine, flips, kind)
        tags = {i: sits[i]["tags"] for i in IDS}
        act = lambda h, Y: v3_act(cat, [c for k in IDS if k != h for c in cards[k]], sits[h], Y, M)
        v2cat, _ = v2_setup(doctrine)
        pert = lambda h: ((ch, M.apply_change(cat, tags[h], [ch])) for ch in
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
## Where each solver is better, worse, or the same

**v3-r2 vs v3-r1 (the round-2 changes).** On DOHA the only v2 rule that moves anything is A5 (a new-against
distinction counts at its *effective* strength in the situation, so a weak factor blocked by a strong
opposite-side factor on the same equity no longer distinguishes). Everything else in v2 (prohibitions, orders,
capped delegations, interim atoms, near-miss scope) is authority machinery that the study delegation switches
off, and SEC-F has no tier floors or prohibitions. A5 makes the solver slightly less brittle: one-tag changes
28/200 (r1: 31) and, with doctrine, it decides DOHA-F-10 again (4/10 vs 3/10) because F-10's weak A20c1 and
A20d@initiated are blocked by the strong B19a/BX1 in F-10 and no longer distinguish DOHA-F-07. Wrong autonomous
acts are unchanged (2/200; 1/230). Accuracy on decided items stays 100%.

**v3-r2 vs solver_v2.** Better on wrong autonomous acts (2 vs 4 of 200; 1 vs 3 of 230) and on one-tag
sensitivity (28 vs 33 of 200; 36 vs 40 of 230). Worse on coverage: 3 vs 4 decided (4 vs 5 with doctrine); the
lost item is DOHA-F-04, which v2 decided only through any-equity downplay (M2), so the loss is the price of the
per-equity fix and v2 rules do not change it.

**Same across all three:** the remaining wrong grants both add `A20d@established` (DOHA-F-01's own dispositive
mitigator) to a denial with no repayment: a perception error the precedent logic must honour. And the
baselines are untouched: a count of A-side tags gets 10/10 (9/10 with a leave-one-out threshold) and 1-NN
8/10 on judge-perception tags, against 3-4/10 decided by any solver. That is circularity in the tags, not
evidence about the solver.

**Consistency.** The DOHA casebook is Horty-consistent under v3-r2 (0 opposite-outcome pairs forcing on the
union of their reasons, with and without doctrine).
"""


def main():
    out = io.StringIO()
    w = lambda s="": out.write(s + "\n")
    w("# DOHA Guideline F pilot, rerun: solver_v2 vs solver_v3 round 1 vs solver_v3 round 2 (spec v2)")
    w()
    w("Generated by `code/doha_study.py`. solver_v2 runs through the pilot's own `run_heldout.py` loaders on")
    w("`catalog-F.yaml`; v3-r1 is `code_r1/solver_v3.py` on `code_r1/` records (spec v1 rules, A5 off); v3-r2 is")
    w("`code/solver_v3.py` on `code/` records (spec v2 rules, A5 on). Tags are judge-perception. Harness action for")
    w("all: act on the settled side, otherwise ask/route; no model distribution, so the study isolates precedent")
    w("logic (as `review/redteam/rt_doha.py` did). For v3 the agent gets a study delegation of both classes so the")
    w("authority gate does not intervene; under the records' real role (`recommend`) every item routes to the judge.")
    w()
    kinds = ("v2", "v3-r1", "v3-r2")
    res = {k: loo(k) for k in kinds}
    resd = {k: loo(k, doctrine=True) for k in kinds}
    w("## Headline (leave-one-out over all 10)")
    w()
    w("| Solver | Catalog | Decided by precedent | Correct when decided | One-tag perturbations that change the action | ...that produce a wrong autonomous act |")
    w("|---|---|---|---|---|---|")
    for lab, R in (("SEAD 4", res), ("SEAD 4 + doctrine", resd)):
        for k in kinds:
            t = R[k][1]
            name = "solver_v2" if k == "v2" else f"solver_v3 {k[3:]}"
            w(f"| {name} | {lab} | {t['decided']}/10 | {t['correct']}/{t['decided']} | {t['changed']}/{t['probes']} | {t['wrong']}/{t['probes']} |")
    w()
    w("## Per case (leave-one-out, SEAD 4 catalog)")
    w()
    w("| Case | Real | v2 | v3-r1 | v3-r2 | one-tag changes v2 / r1 / r2 |")
    w("|---|---|---|---|---|---|")
    for r2, r1, r3 in zip(res["v2"][0], res["v3-r1"][0], res["v3-r2"][0]):
        w(f"| {r2[0]} | {NAMES[r2[1]]} | {r2[2]} -> {NAMES[r2[3]]} | {r1[2]} -> {NAMES[r1[3]]} | {r3[2]} -> {NAMES[r3[3]]} | "
          f"{r2[5]} / {r1[5]} / {r3[5]} |")
    w()
    w("## Kinds of action change under one-tag perturbation (SEAD 4)")
    w()
    w("| Solver | act -> ask | ask -> act (right) | ask -> act (WRONG) | act -> act (flipped) |")
    w("|---|---|---|---|---|")
    for k in kinds:
        t = res[k][1]
        w(f"| {k} | {t['act->ask']} | {t['ask->act(right)']} | {t['ask->act(WRONG)']} | {t['act->act(flipped)']} |")
    w()
    for k in kinds:
        w(f"Wrong autonomous acts, {k}: " + ("; ".join(res[k][2]) or "none"))
        w()
    w("## Baselines (same tags, same 10 cases)")
    w()
    cat3 = S.load_catalog(os.path.join(HERE, "catalogs/SEC-F.yaml"))
    b = baselines(res["v3-r2"][3], res["v3-r2"][4], lambda t: cat3.side(t) if t in cat3.tag else None)
    w("| Rule | Correct |")
    w("|---|---|")
    for name, n in b.items():
        w(f"| {name} | {n}/10 |")
    for k in kinds:
        w(f"| {k}, decided by precedent (rest ask/route) | {res[k][1]['correct']}/10 correct, {10 - res[k][1]['decided']} ask |")
    w()
    c = S.load_catalog(os.path.join(HERE, "catalogs/SEC-F.yaml"))
    for fl in ((), ("doctrine",)):
        cc = S.load_catalog(os.path.join(HERE, "catalogs/SEC-F.yaml"), fl)
        cards = [x for i in IDS for x in S.cards_from_record(cc, S.load_yaml(os.path.join(HERE, f"records/{i}.yaml")), with_flips=False)]
        w(f"Horty/naqd lint, v3-r2, {'with' if fl else 'without'} doctrine: {len(S.lint_horty(cc, cards))} inconsistent pairs.")
    w(INTERPRETATION)
    with open(os.path.join(HERE, "results/doha-v3.md"), "w") as fh:
        fh.write(out.getvalue())
    print(out.getvalue())


if __name__ == "__main__":
    main()
