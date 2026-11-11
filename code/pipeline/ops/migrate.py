"""Map the lineage of scenarios built before the operator spec onto the new operator names and arguments
(OPERATORS-SPEC-v1 §Mapping). Additive: adds `lineage.anchor` and one `lineage.steps` entry (marked `migrated: true`)
built from the legacy `lineage.operator` / `detail` and, where it exists, the gold partial; nothing is removed.
store.write_yaml keeps the previous file in versions/. Dry run by default.

    python -m pipeline.ops migrate [--apply]
"""
from __future__ import annotations

import time
from collections import Counter
from pathlib import Path

import yaml

from bench.schema.pipeline import Scenario
from pipeline.store import Store, write_yaml

from .record import SPEC

LEGACY = {  # legacy operator -> (op, mode, args from detail)
    "restyle": ("surface_edit", "reword", lambda d: {"surface_distance": d.get("surface_distance")}),
    "flip": ("structural_edit", "flip", lambda d: {"target": {"phi": d.get("phi")}, "realization": (
        "plain" if "paraphrase" in str((d.get("indirectness") or {}).get("skipped", "")) else "indirect"),
        "note": "pipeline.perturb.flip (also restyled lightly)", "legacy_how": d.get("how")}),
    "add_fact": ("structural_edit", "target_f", lambda d: {"target": {"new_fact": d.get("new_fact")}, "solver_legacy": d.get("solver")}),
    "revise_card": ("judgment_edit", None, lambda d: {"target": d.get("target"), "weights_only": False,
                                                       "legacy_delta_k": d.get("delta_k")}),
    "reorder": ("permute", None, lambda d: {"target": "options", "order": {"gold_to": d.get("gold_position")}, "id_map": d.get("perm")}),
    "transfer": ("surface_edit", "transfer", lambda d: {"setting": {k: d.get(k) for k in ("subdomain", "sister", "sketch_file")},
                                                       "then_permuted": d.get("option_permutation")}),
    "transfer-flip": ("structural_edit", "flip", lambda d: {"target": {"phi": (d.get("flip_item") or {}).get("id")}, "realization": "plain",
                                                           "composed_with": "permute (options, inherited from the sister)"}),
}


def legacy_files(store: Store):
    for p in sorted((store.root / "scenarios").glob("*/*.yaml")):
        yield p, "accepted"
    for b, d in (("hard", "transfer-hard"), ("rejected", "transfer-rejected")):
        for p in sorted((store.root / d).glob("*.yaml")):
            yield p, b


def plan(store: Store | None = None) -> list[dict]:
    store = store or Store()
    docs = {}
    for p, b in legacy_files(store):
        d = yaml.safe_load(p.read_text())
        docs[d["id"]] = (p, b, d)
    out = []
    for sid, (p, b, d) in docs.items():
        lin = d.get("lineage") or {}
        op = lin.get("operator")
        if not lin.get("parent") or lin.get("steps") or op not in LEGACY:
            continue
        cur, seen = lin.get("parent"), set()
        while cur in docs and (docs[cur][2].get("lineage") or {}).get("parent") and cur not in seen:
            seen.add(cur)
            cur = docs[cur][2]["lineage"]["parent"]
        new_op, mode, argf = LEGACY[op]
        detail = lin.get("detail") or {}
        partial = store.root / "partials" / f"{sid}.yaml"
        if not partial.exists():
            partial = store.root / "partials" / "revised" / f"{sid}.yaml"
        delta = yaml.safe_load(partial.read_text()) if partial.exists() else None
        step = {"op": new_op, "mode": mode, "args": argf(detail), "parent": lin["parent"], "writer": None, "solver": None,
                "gates": (detail.get("checks") or {}) and {"legacy_checks": True}, "annotations": {}, "intended": None,
                "delta": {k: delta[k] for k in ("options_map", "fact_map", "consideration_map", "relation", "via", "choice",
                                                 "gold_tier") if delta and k in delta} or None,
                "bucket": b, "bucket_why": "legacy bucket", "spec": SPEC, "migrated": True, "legacy_operator": op,
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        out.append({"id": sid, "path": str(p), "anchor": cur, "step": step})
    return out


def apply(rows: list[dict]) -> int:
    n = 0
    for r in rows:
        p = Path(r["path"])
        d = yaml.safe_load(p.read_text())
        d["lineage"]["anchor"] = r["anchor"]
        d["lineage"]["steps"] = [r["step"]]
        Scenario.model_validate(d)
        write_yaml(p, d)
        n += 1
    return n


def summary(rows: list[dict]) -> dict:
    return {"n": len(rows), "by_legacy": dict(Counter(r["step"]["legacy_operator"] for r in rows)),
            "with_delta": sum(1 for r in rows if r["step"]["delta"]), "anchors": len({r["anchor"] for r in rows})}
