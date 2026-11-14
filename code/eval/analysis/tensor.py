"""The ablation tensor: every reply of every registered run as one tidy table, and views over it (2026-11-10).

Storage. `measurements/runs.yaml` registers each run directory as one condition (its factor values: policy, scaffold,
thinking, ...). `build` reads every registered run's samples.jsonl (+ raw reply and judge details where a metric
needs them) and writes results/tensor/replies.parquet: one row per reply, columns = factors + coordinates (arm, x1,
x2, idx, family) + outcomes. Deterministic given the runs; no LLM calls (the option translation was done by the Jev
judge at scoring time and is read from the samples).

Outcomes per reply:
  correct        verdict maps to X1's gold option (unscored / no verdict count as 0, as in the reports)
  off_menu       a verdict was given but maps to no gold option
  no_verdict     no parsable verdict choice
  copied         transfer/flip arms: the choice equals the served case's verdict (mapped to X1's options), else NaN
  contamination  share of the reply's own enumerated considerations that favor the flipped sister's verdict (X1s
                 with a flip cell; schema scaffold only, since guided/free have no structured considerations), else NaN
  relation       verdict.relation (schema scaffold with a case), else None
  choice         the verdict mapped onto X1's options (Jev translation), else None (for agreement with no case)
  truncated, completion_tokens, thinking_chars

Views. A metric is aggregated as the mean over X1 of each X1's mean (X1 = the unit of inference), with a 95%
family-bootstrap CI (scenario families resampled). Contrasts are paired per X1 (only X1s present on both sides).

    PYTHONPATH=code .venv/bin/python -m eval.analysis.tensor build
    PYTHONPATH=code .venv/bin/python -m eval.analysis.tensor view --metric correct --rows policy scaffold thinking --cols arm
    PYTHONPATH=code .venv/bin/python -m eval.analysis.tensor contrast --factor scaffold --a guided --b free --by policy arm
    PYTHONPATH=code .venv/bin/python -m eval.analysis.tensor standard --out measurements/views/SCAFFOLD-ABLATION.md
Common options: --where key=value ... (filter), --max-idx N (only samples idx <= N, for runs of unequal k).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import mean

import pandas as pd
import yaml

from eval.allpairs_report import fam_boot

REGISTRY = Path("measurements/runs.yaml")
OUT = Path("results/tensor/replies.parquet")
FACTORS = ["policy", "scaffold", "thinking", "max_tokens", "mode_line", "cells", "traces", "equities", "card_view",
           "scoring", "run", "status"]
ARM_ORDER = ["control", "self", "transfer", "flip", "decoy"]
# arms whose served case has its own verdict to copy (pilot-2 names + pairs-v1 names, 2026-11-14). On the flip arms
# copying is the error; on the follows arms it coincides with being right.
COPY_ARMS = {"transfer", "flip", "transfer_flip", "same_domain_flip", "flip_neighbor", "neighbor", "noflip",
             "xd_neighbor", "xd_noflip"}


def _ok(v):
    return 0.0 if v is None else float(v)


def build(registry: Path = REGISTRY, out: Path = OUT, contamination: bool = True) -> pd.DataFrame:
    from bench.schema import parse_reply
    from pipeline.store import Store
    from eval.core import read_samples
    from eval.transfer_report import case_verdict_as_x1
    reg = yaml.safe_load(registry.read_text())
    store, cv, rows = Store(), {}, []
    for ent in reg["runs"]:
        f = {**reg.get("defaults", {}), **ent}
        d = Path(f["run"])
        if not (d / "samples.jsonl").exists():
            continue
        S = read_samples(d / "samples.jsonl")
        flipopt: dict[str, set] = {}
        for r in S:
            if r["phase"] == "flip" and r.get("x2"):
                cv.setdefault(r["x2"], case_verdict_as_x1(store, r["x2"]))
                flipopt.setdefault(r["x1"], set()).add(cv[r["x2"]])
        for r in S:
            arm = r["phase"]
            copied = math.nan
            if arm in COPY_ARMS and r.get("x2"):
                cv.setdefault(r["x2"], case_verdict_as_x1(store, r["x2"]))
                copied = float(r.get("translated_choice") == cv[r["x2"]])
            contam = math.nan
            if contamination and f["scaffold"] == "schema" and r["x1"] in flipopt and r.get("details_path") \
                    and (d / r["details_path"]).exists():
                tr = (json.loads((d / r["details_path"]).read_text()).get("option_alignment") or {}).get("translation") or {}
                ce = parse_reply((d / r["raw_path"]).read_text()).steps.get("consideration_enumeration") or {}
                fav = [set(tr.get(o) for o in (x.get("favors") or []) if isinstance(o, str)) - {None}
                       for x in (ce.get("considerations") or []) if isinstance(x, dict)]
                fav = [s for s in fav if s]
                if fav:
                    contam = mean(bool(s & flipopt[r["x1"]]) for s in fav)
            t = r.get("tokens") or {}
            rows.append({**{k: f.get(k) for k in FACTORS}, "measurement": f.get("measurement"),
                         "arm": arm, "x1": r["x1"], "x2": r.get("x2"), "idx": r["idx"], "family": r.get("x1_family"),
                         "sample_id": r["sample_id"], "correct": _ok(r.get("correct")),
                         "scored": r.get("correct") is not None, "off_menu": float(bool(r.get("off_menu"))),
                         "no_verdict": float(r.get("parsed_choice") is None), "copied": copied,
                         "choice": r.get("translated_choice"),
                         "contamination": contam, "relation": r.get("model_relation"),
                         "truncated": float(r.get("finish_reason") == "length"),
                         "completion_tokens": t.get("completion"), "thinking_chars": t.get("thinking_chars"),
                         "raw_path": str(d / r["raw_path"])})
    df = pd.DataFrame(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    return df


def load(where: list[str] | None = None, max_idx: int | None = None, path: Path = OUT) -> pd.DataFrame:
    df = pd.read_parquet(path)
    for w in where or []:
        k, v = w.split("=", 1)
        df = df[df[k].astype(str) == v]
    if max_idx is not None:
        df = df[df["idx"] <= max_idx]
    return df


def agg(df: pd.DataFrame, metric: str) -> tuple[float, float, float, int, int]:
    """-> (mean over X1, lo, hi, n_x1, n_replies) for one cell of a view."""
    d = df.dropna(subset=[metric])
    if d.empty:
        return (math.nan,) * 3 + (0, 0)
    per = d.groupby("x1")[metric].mean().to_dict()
    fam = d.groupby("x1")["family"].first().to_dict()
    m, lo, hi = fam_boot(per, fam)
    return m, lo, hi, len(per), len(d)


def fmt(t, pct=True) -> str:
    m, lo, hi, nx, n = t
    if n == 0:
        return "—"
    return (f"{100*m:.0f}% [{100*lo:.0f}-{100*hi:.0f}]" if pct else f"{m:.2f} [{lo:.2f}-{hi:.2f}]") + f" n={n}"


def _key(v):
    return ARM_ORDER.index(v) if v in ARM_ORDER else 99, str(v)


def view(df: pd.DataFrame, metric: str, rows: list[str], cols: list[str]) -> str:
    rk = sorted({tuple(r) for r in df[rows].astype(str).values.tolist()})
    ck = sorted({tuple(c) for c in df[cols].astype(str).values.tolist()}, key=lambda c: [_key(x) for x in c])
    L = [f"| {' / '.join(rows)} | " + " | ".join(" / ".join(c) for c in ck) + " |", "|---|" + "---|" * len(ck)]
    for r in rk:
        sub = df[(df[rows].astype(str) == list(r)).all(axis=1)]
        cells = [fmt(agg(sub[(sub[cols].astype(str) == list(c)).all(axis=1)], metric)) for c in ck]
        L.append(f"| {' / '.join(r)} | " + " | ".join(cells) + " |")
    return "\n".join(L)


def contrast(df: pd.DataFrame, metric: str, factor: str, a: str, b: str, by: list[str]) -> str:
    """Paired per-X1 difference (a - b) of the metric, within each combination of `by`."""
    L = [f"| {' / '.join(by)} | {factor}: {a} − {b} (points) | X1s |", "|---|---|---|"]
    keys = sorted({tuple(x) for x in df[by].astype(str).values.tolist()}, key=lambda c: [_key(x) for x in c])
    for k in keys:
        sub = df[(df[by].astype(str) == list(k)).all(axis=1)].dropna(subset=[metric])
        A = sub[sub[factor].astype(str) == a].groupby("x1")[metric].mean()
        B = sub[sub[factor].astype(str) == b].groupby("x1")[metric].mean()
        xs = sorted(set(A.index) & set(B.index))
        if not xs:
            continue
        fam = sub.groupby("x1")["family"].first().to_dict()
        m, lo, hi = fam_boot({x: A[x] - B[x] for x in xs}, fam)
        L.append(f"| {' / '.join(k)} | {100*m:+.0f} [{100*lo:+.0f}, {100*hi:+.0f}] | {len(xs)} |")
    return "\n".join(L)


def standard(df: pd.DataFrame, max_idx: int | None) -> str:
    """The designed views of the scaffold ablation (M11)."""
    have = df.groupby(["policy", "scaffold", "thinking"]).size().to_dict()
    L = ["# Scaffold ablation: views over the tensor", "",
         "Generated by `PYTHONPATH=code .venv/bin/python -m eval.analysis.tensor standard"
         + (f" --max-idx {max_idx}" if max_idx is not None else "") + "` from `results/tensor/replies.parquet` "
         "(built from `measurements/runs.yaml`). Cells: mean over X1 of per-X1 mean, 95% family-bootstrap CI, n = replies.",
         "", "Conditions present (policy / scaffold / thinking: replies):", ""]
    L += [f"- {p} / {s} / {t}: {n}" for (p, s, t), n in sorted(have.items())]
    L += ["", "## Accuracy against X1's key", "", view(df, "correct", ["policy", "scaffold", "thinking"], ["arm"]),
          "", "## Copies the served case's verdict (transfer, flip)", "",
          view(df[df.arm.isin(["transfer", "flip"])], "copied", ["policy", "scaffold", "thinking"], ["arm"]),
          "", "## Off-menu (a verdict that maps to no option of X1)", "",
          view(df, "off_menu", ["policy", "scaffold", "thinking"], ["arm"]),
          "", "## No parsable verdict", "", view(df, "no_verdict", ["policy", "scaffold", "thinking"], ["arm"]),
          "", "## Guidance effect: guided − free (same policy, same thinking)", "",
          contrast(df, "correct", "scaffold", "guided", "free", ["policy", "thinking", "arm"]),
          "", "## Schema effect: schema − guided (same policy, same thinking)", "",
          contrast(df, "correct", "scaffold", "schema", "guided", ["policy", "thinking", "arm"]),
          "", "## Case benefit within each scaffold: arm − no case", ""]
    for arm in ("self", "transfer", "flip", "decoy"):
        L += [f"### {arm} − control", "", contrast(df, "correct", "arm", arm, "control", ["policy", "scaffold", "thinking"]), ""]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["build", "view", "contrast", "standard"])
    ap.add_argument("--metric", default="correct")
    ap.add_argument("--rows", nargs="+", default=["policy", "scaffold", "thinking"])
    ap.add_argument("--cols", nargs="+", default=["arm"])
    ap.add_argument("--factor")
    ap.add_argument("--a")
    ap.add_argument("--b")
    ap.add_argument("--by", nargs="+", default=["policy", "arm"])
    ap.add_argument("--where", nargs="*", default=[])
    ap.add_argument("--max-idx", type=int)
    ap.add_argument("--out")
    ap.add_argument("--no-contamination", action="store_true", help="build: skip the (slower) contamination metric")
    a = ap.parse_args(argv)
    if a.cmd == "build":
        df = build(contamination=not a.no_contamination)
        print(df.groupby(["run", "policy", "scaffold", "thinking"]).size().to_string())
        return 0
    df = load(a.where, a.max_idx)
    text = (view(df, a.metric, a.rows, a.cols) if a.cmd == "view"
            else contrast(df, a.metric, a.factor, a.a, a.b, a.by) if a.cmd == "contrast"
            else standard(df, a.max_idx))
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
