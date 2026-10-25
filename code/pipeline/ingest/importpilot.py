"""import-pilot: the 10 converted pilot cases (data/cases/**/DR-*.case.yaml, 2b) -> eval-only Scenarios in the store.

Copy only: data/cases/ and data/scenarios/ are never written. The v2.6 card each case was converted from (named in
data/cases/MANIFEST.yaml) is the SourceRef: sha256 of that file, doc = its repo path. The card's holding is Claude-drafted
and awaits Peter's review, so `verdict_tier` source-endorsed is a stretch; `basis` says so and status stays needs_review.
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

import yaml

from bench.schema import Case
from bench.schema.pipeline import Lineage, ProvStep, Provenance, Scenario, SourceRef
from pipeline.store import DATA, ROOT, Store


def _rel(f: Path, base: Path) -> str:
    try:
        return str(f.relative_to(base))
    except ValueError:
        return str(f)


def import_pilot(data: Path = DATA, root: Path = ROOT) -> list[str]:
    manifest = {c["id"]: c for c in yaml.safe_load((data / "cases" / "MANIFEST.yaml").read_text())["cases"]}
    st = Store(data)
    out = []
    for f in sorted((data / "cases").glob("*/DR-*.case.yaml")):
        raw = f.read_bytes()
        case = Case.model_validate(yaml.safe_load(raw))
        lib = case.library or {}
        m = manifest.get(case.id, {})
        src_rel = m.get("source")
        src_file = root / src_rel if src_rel else None
        if src_file and src_file.exists():
            ref = SourceRef(sha256=hashlib.sha256(src_file.read_bytes()).hexdigest(), doc=src_rel, kind="v2.6 reference card (Claude-drafted)")
        else:
            ref = SourceRef(sha256=hashlib.sha256(raw).hexdigest(), doc=_rel(f, root), kind="2b converted case file")
        prov = Provenance(
            steps=[ProvStep(id="import", operator="import", inputs={"case_file": hashlib.sha256(raw).hexdigest(), "card": ref.sha256},
                            ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            notes="copied from data/cases (2b conversion of a v2.6 card by the converter role); not modified")],
            fields={"case": "import"}, authored=["case.facts", "case.considerations", "case.reasoning", "case.flip_conditions"])
        s = Scenario(id=case.id, family=lib.get("family") or case.id.split("@")[0][3:], split="eval-only", domain=lib.get("domain", "unknown"),
                     status="needs_review", case=case, verdict_tier="source-endorsed",
                     basis="v2.6 card holding (Claude-drafted reference card, converted by 2b; not yet reviewed by Peter)",
                     source=ref, fact_spans={f_.id: [] for f_ in case.facts}, tags=["eval-only-import"],
                     lineage=Lineage(operator="import", detail={"case_file": _rel(f, root)}), provenance=prov)
        st.save_scenario(s)
        out.append(s.id)
    return out
