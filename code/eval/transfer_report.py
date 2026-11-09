"""Report for the cross-domain transfer pilot (eval.allpairs run with --cells; arms = phases).

    PYTHONPATH=code .venv/bin/python -m eval.transfer_report --run results/transfer/pilot1

Per arm: verdict accuracy against X1's own answer key (mean over X1 of its per-X1 rate, 95% family-bootstrap CI),
and for the transfer and flip arms the COPY rate: how often the model picked the X1 option that corresponds to the
served case's verdict (sister options map one-to-one to the anchor's; the sister's option ids are shuffled, and the
shuffle is undone with lineage.detail.option_permutation). On the transfer arm, copying and being right coincide; on
the flip arm the case's verdict is NOT X1's answer, so copy rate vs accuracy separates copying from reasoning.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from .allpairs_report import fam_boot, ok, pct
from .core import read_samples

ARM_ORDER = ["control", "self", "transfer", "flip", "decoy"]
ARM_LABEL = {"control": "no case", "self": "own case (X2 = X1)", "transfer": "transferred sister (same K)",
             "flip": "transferred sister, flipped (verdict differs)", "decoy": "sister of another anchor (different K)"}


def case_verdict_as_x1(store, x2: str) -> str | None:
    S = store.scenario(x2)
    perm = (S.lineage.detail or {}).get("option_permutation") or {}
    inv = {v: k for k, v in perm.items()}
    v = S.case.verdict.choice
    return "LIVE-" + inv.get(v, v)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    a = ap.parse_args(argv)
    from pipeline.store import Store
    store = Store()
    run = Path(a.run)
    S = read_samples(run / "samples.jsonl")
    fam = {r["x1"]: r.get("x1_family") for r in S}
    by = defaultdict(lambda: defaultdict(list))         # arm -> x1 -> [correct]
    cp = defaultdict(lambda: defaultdict(list))         # arm -> x1 -> [copied]
    cv_cache = {}
    for r in S:
        arm = r["phase"]
        by[arm][r["x1"]].append(ok(r["correct"]))
        if arm in ("transfer", "flip") and r.get("x2"):
            if r["x2"] not in cv_cache:
                cv_cache[r["x2"]] = case_verdict_as_x1(store, r["x2"])
            cp[arm][r["x1"]].append(1.0 if r.get("translated_choice") == cv_cache[r["x2"]] else 0.0)
    L = [f"# Transfer pilot: {run.name}", "", f"{len(S)} samples, {len(fam)} X1s.", "",
         "| arm | X1s | samples | accuracy (vs X1's key) | copies the case's verdict |", "|---|---|---|---|---|"]
    for arm in ARM_ORDER + sorted(set(by) - set(ARM_ORDER)):
        if arm not in by:
            continue
        d = {x: mean(v) for x, v in by[arm].items()}
        n = sum(len(v) for v in by[arm].values())
        c = pct(fam_boot({x: mean(v) for x, v in cp[arm].items()}, fam)) if arm in cp else "—"
        L.append(f"| {ARM_LABEL.get(arm, arm)} | {len(d)} | {n} | {pct(fam_boot(d, fam))} | {c} |")
    # paired differences per X1 (same X1 in both arms)
    L += ["", "Paired per-X1 differences (mean over X1s present in both arms):", ""]
    for a1, a2 in (("transfer", "control"), ("transfer", "decoy"), ("self", "control"), ("flip", "control")):
        xs = [x for x in by[a1] if x in by[a2]]
        if xs:
            dif = {x: mean(by[a1][x]) - mean(by[a2][x]) for x in xs}
            m, lo, hi = fam_boot(dif, fam)
            L.append(f"- {ARM_LABEL[a1]} − {ARM_LABEL[a2]}: {100 * m:+.0f} points [{100 * lo:+.0f}, {100 * hi:+.0f}] ({len(xs)} X1s)")
    md = "\n".join(L) + "\n"
    (run / "report.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
