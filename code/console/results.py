"""Results explorer data (Peter, 2026-11-13: "a nice interactive page on the console to explore the results").

Source: the ablation tensor (results/tensor/replies.parquet, one row per reply of every run in measurements/runs.yaml;
`python -m eval.analysis.tensor build` refreshes it). Every number here is the tensor method: the mean over X1 of
each X1's mean, with a 95% family-bootstrap CI (eval.allpairs_report.fam_boot). No LLM calls.

Arms are reported per case-trace relationship (Peter, 2026-11-13: report performance broken down by each
relationship). The pilot-2 arm names map onto those relationships in ARMS; pairs-v1 arm names are listed too so its
eval runs show up under the same labels once registered.

The summary is cached next to the tensor (results/tensor/summary.json) and rebuilt when the tensor changes.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TENSOR = ROOT / "results" / "tensor" / "replies.parquet"
CACHE = ROOT / "results" / "tensor" / "summary.json"
VERSION = 6                                    # bump when the summary's fields change (invalidates the cache)

# arm -> (relationship label, what the served case is, expected relation). Order = display order.
ARMS = {
    "control": ("No case", "nothing served; the baseline", None),
    "self": ("Own case", "X1's own case (identity)", "follows"),
    "neighbor": ("In-domain neighbor", "same sub-domain, a different situation, same K and V", "follows"),
    "transfer": ("Cross-domain transfer", "K and V carried into another national-security domain, F rebuilt",
                 "follows"),
    "xd_neighbor": ("Cross-domain neighbor", "a neighbor of a cross-domain transfer: F changes slightly, K and V fixed",
                    "follows"),
    "noflip": ("Non-flip edit", "a would-not-change condition made true: facts change, V holds", "follows"),
    "xd_noflip": ("Cross-domain non-flip edit", "a cross-domain transfer with a would-not-change condition made true",
                  "follows"),
    "same_domain_flip": ("In-domain flip", "a would-change condition made true in X1's own domain", "flips"),
    "flip_neighbor": ("Flip-neighbor", "a neighbor of an in-domain flip: F changes slightly, the flipped K and V fixed",
                      "flips"),
    "flip": ("Flip-transfer", "a cross-domain transfer with a would-change condition made true", "flips"),
    "transfer_flip": ("Flip-transfer", "a cross-domain transfer with a would-change condition made true", "flips"),
    "revised": ("Revised case", "the case's judgment edited (C')", "follows"),
    "decoy": ("Unrelated case", "another anchor's (cross-domain) case", "not_governed"),
    "random": ("Unrelated case", "another anchor's case", "not_governed"),
}
ARM_ORDER = list(ARMS)

# display names, in the fixed categorical order the page colors them by (color follows the model, never its rank)
POLICIES = {
    "gpt-6-luna": "GPT-6 Luna",
    "granite-4.2-8b": "Granite 4.2 8B",
    "qwen3.5-9b": "Qwen3.5 9B",
    "olmo-3-7b-think": "Olmo 3 7B Think",
    "ministral-3-14b-reasoning": "Ministral 3 14B",
    "gemma-4-12b-it": "Gemma 4 12B",
    "granite-4.2-8b+sft-gen1": "Granite SFT gen1",
    "granite-4.2-8b+sft-gen1-ckpt300": "Granite SFT gen1 (step 300)",
}
DATASETS = {"pilot2": "pilot 2 (28 X1s; M06-M11)", "pv1-val": "pairs-v1 val (61 X1s)", "pv1-test": "pairs-v1 test"}
SCAFFOLDS = ["free", "guided", "schema", "v4"]

# The size-class comparison (M11) uses the v2 mode-A line everywhere except Granite schema, whose think-first run
# is M09 (mode line v1.A). The two older schema runs (Granite YAML-in-thinking M07, Luna with the v1 mode-C line M06)
# are "earlier variants": shown only on request, never mixed into the comparison.
EARLIER = {"results/transfer/pilot2", "results/transfer/pilot2-luna"}

METRICS = {
    "correct": ("Accuracy (as scored)", "Choice maps to X1's gold option. Unreadable replies count as wrong."),
    "correct_readable": ("Accuracy (readable replies)",
                         "Same, over readable replies only (a parsable verdict that maps to one of X1's options). "
                         "Selection-biased if the unreadable replies are the harder items."),
    "readable": ("Readable share", "Replies with a parsable verdict that maps to one of X1's options."),
    "copied": ("Copied the served verdict", "Transfer / flip arms: the choice equals the served case's verdict, "
               "mapped onto X1's options. On a flip arm, copying is the error."),
    "agree_nocase": ("Agrees with own no-case choice",
                     "Chance that this reply's choice equals a random no-case reply of the same model, scaffold and X1 "
                     "(readable replies on both sides). The headline for the unrelated arm (Peter, 2026-11-13): an "
                     "irrelevant case should not move the model. On other arms it shows how far the case moved it."),
    "modal_nocase": ("Matches modal no-case choice",
                     "The reply's choice is the model's most common no-case choice on the same X1 (readable replies; "
                     "a no-case reply is compared with the other no-case replies)."),
    "relation_ok": ("Relation label correct",
                    "The verdict's relation (follows / flips / distinguished / not_governed) is the one the arm "
                    "expects (see the Relationships table). Over replies with a verdict; formats with a relation field "
                    "only (schema, v4). A missing label counts as wrong."),
    "said_not_governed": ("Labelled not_governed",
                          "Share of replies with a verdict whose relation is not_governed. On the unrelated arm it is "
                          "the second half of Peter's metric (2026-11-13); on the other arms it is a wrong refusal of "
                          "a relevant case."),
    "off_menu": ("Off-menu", "A verdict was given but maps to none of X1's options."),
    "no_verdict": ("No verdict", "No parsable verdict choice."),
    "truncated": ("Truncated", "Generation hit max_tokens."),
}


def _boot(d, col):
    from eval.allpairs_report import fam_boot
    d = d.dropna(subset=[col])
    if d.empty:
        return None
    per = d.groupby("x1")[col].mean().to_dict()
    fam = d.groupby("x1")["family"].first().to_dict()
    m, lo, hi = fam_boot(per, fam, B=1000)
    if m != m:
        return None
    return {"m": round(m, 4), "lo": round(lo, 4), "hi": round(hi, 4), "nx": len(per), "n": int(len(d))}


def _build() -> dict:
    import pandas as pd
    t = pd.read_parquet(TENSOR)
    t["run"] = t["run"].astype(str).str.rstrip("/")
    t["readable"] = (t["scored"].astype(bool) & (t["off_menu"] == 0) & (t["no_verdict"] == 0)).astype(float)
    t["correct_readable"] = t["correct"].where(t["readable"] == 1)
    # agreement with the same run's no-case replies on the same X1 (readable choices only). A no-case reply is compared
    # with the OTHER no-case replies (leave-one-out), so the control row is the model's own sampling consistency: the
    # baseline the other arms are read against.
    nc = t[(t["arm"] == "control") & (t["readable"] == 1) & t["choice"].notna()]
    counts = {k: g["choice"].value_counts().to_dict() for k, g in nc.groupby(["run", "x1"])}

    def _agree(r, modal):
        cnt = counts.get((r["run"], r["x1"]))
        if cnt is None or r["readable"] != 1 or r["choice"] is None:
            return float("nan")
        cnt = dict(cnt)
        if r["arm"] == "control":
            cnt[r["choice"]] -= 1
        n = sum(cnt.values())
        if n <= 0:
            return float("nan")
        if modal:
            top = max(cnt.values())
            return float(cnt.get(r["choice"], 0) == top and top > 0)
        return cnt.get(r["choice"], 0) / n
    # relation labels: only for formats that ask for one (schema, v4) and arms that serve a case
    has_rel = t["scaffold"].isin(["schema", "v4"]) & (t["arm"] != "control") & t["scored"].astype(bool) \
        & (t["no_verdict"] == 0)
    expect = t["arm"].map(lambda a: ARMS.get(a, (None, None, None))[2])
    rel = t["relation"].fillna("")
    t["relation_ok"] = (rel == expect).astype(float).where(has_rel & expect.notna())
    t["said_not_governed"] = (rel == "not_governed").astype(float).where(has_rel)
    recs = t.to_dict("records")
    t["agree_nocase"] = [_agree(r, False) for r in recs]
    t["modal_nocase"] = [_agree(r, True) for r in recs]
    rows = []
    for (run, arm), g in t.groupby(["run", "arm"], sort=False):
        f = g.iloc[0]
        rows.append({
            "run": run, "policy": f["policy"], "model": POLICIES.get(f["policy"], f["policy"]),
            "scaffold": f["scaffold"], "thinking": f["thinking"], "mode_line": f["mode_line"],
            "measurement": f.get("measurement"), "status": f["status"], "variant": "earlier" if run in EARLIER else "main",
            "cells": f["cells"], "arm": arm, "relationship": ARMS.get(arm, (arm,))[0], "k": int(g["idx"].max()) + 1,
            "metrics": {k: _boot(g, k) for k in METRICS},
        })
    return {"version": VERSION, "tensor_mtime": TENSOR.stat().st_mtime, "rows": rows}


def summary() -> dict:
    """The page's data: one row per (run, arm) with every metric (mean over X1, 95% family-bootstrap CI)."""
    if not TENSOR.exists():
        return {"rows": [], "missing": str(TENSOR.relative_to(ROOT))}
    try:
        c = json.loads(CACHE.read_text())
        if c.get("version") == VERSION and c.get("tensor_mtime") == TENSOR.stat().st_mtime:
            s = c
        else:
            raise ValueError
    except (OSError, ValueError):
        s = _build()
        CACHE.write_text(json.dumps(s))
    present = {r["arm"] for r in s["rows"]}
    rels = []
    for a, (label, what, rel) in ARMS.items():
        if label in {x["label"] for x in rels}:
            rels[[x["label"] for x in rels].index(label)]["arms"].append(a)
            if a in present:
                rels[[x["label"] for x in rels].index(label)]["measured"] = True
            continue
        rels.append({"label": label, "what": what, "relation": rel, "arms": [a], "measured": a in present})
    pending = []
    try:
        import yaml
        reg = yaml.safe_load((ROOT / "measurements" / "runs.yaml").read_text())
        pending = [{"run": e["run"], "model": POLICIES.get(e["policy"], e["policy"]), "scaffold": e["scaffold"],
                    "status": e.get("status")} for e in reg["runs"] if e.get("status") not in ("complete",)]
    except Exception:                                                   # noqa: BLE001
        pass
    return {**s, "arm_order": ARM_ORDER, "relationships": rels, "policies": POLICIES, "scaffolds": SCAFFOLDS,
            "metrics": {k: {"label": v[0], "help": v[1]} for k, v in METRICS.items()}, "pending": pending,
            "datasets": {k: DATASETS.get(k, k) for k in dict.fromkeys(r["cells"] for r in s["rows"])},
            "tensor": str(TENSOR.relative_to(ROOT)), "built": _iso(s.get("tensor_mtime"))}


def _iso(ts):
    import time
    return None if ts is None or (isinstance(ts, float) and math.isnan(ts)) else \
        time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(ts))
