"""Registry: sources.seed.yaml -> data/store/registry/sources.yaml (+ acquired.yaml bookkeeping)."""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import yaml

from pipeline.store import DATA, ROOT, write_yaml

SEED = Path(__file__).with_name("sources.seed.yaml")
REG_DIR = DATA / "store" / "registry"
CATALOG = ROOT / "context" / "sources" / "source-catalog.csv"
REQUIRED = ("id", "url", "format", "kind", "license", "why", "domain", "episodes")


def load_seed() -> list[dict]:
    return yaml.safe_load(SEED.read_text())["sources"]


def catalog_rows() -> set[tuple[str, str]]:
    if not CATALOG.exists():
        return set()
    with open(CATALOG, newline="") as f:
        return {(r["strand"], r["source"]) for r in csv.DictReader(f)}


def validate(sources: list[dict], catalog: set[tuple[str, str]] | None = None) -> list[str]:
    errs, seen = [], set()
    for s in sources:
        errs += [f"{s.get('id')}: missing {k}" for k in REQUIRED if not s.get(k)]
        if s.get("id") in seen:
            errs.append(f"duplicate id {s['id']}")
        seen.add(s.get("id"))
        if "public domain" not in str(s.get("license", "")).lower():
            errs.append(f"{s.get('id')}: license is not recorded as public domain")
        if catalog:
            row = s.get("catalog_row") or {}
            if (row.get("strand"), row.get("source", "").split(" (nearest")[0]) not in catalog:
                errs.append(f"{s.get('id')}: catalog row {row} not in source-catalog.csv")
    return errs


def family_of(source: dict, ep: dict) -> str:
    return ep.get("family") or source["family"]


def families(sources: list[dict]) -> list[str]:
    return sorted({family_of(s, e) for s in sources for e in s["episodes"]})


def assign_splits(fams: list[str]) -> dict[str, str]:
    """Deterministic per-family split. Order families by sha256(family); the first is `test`, the second `dev`,
    the rest `train` (needs >= 3 families; with fewer, everything is train and the caller must say so)."""
    order = sorted(set(fams), key=lambda f: hashlib.sha256(f.encode()).hexdigest())
    if len(order) < 3:
        return {f: "train" for f in order}
    return {f: ("test" if i == 0 else "dev" if i == 1 else "train") for i, f in enumerate(order)}


SPLIT_RULE = ("families sorted by sha256(family id); first -> test, second -> dev, remaining -> train; "
              "fewer than 3 families -> all train. Splits are per family, assigned before any perturbation.")


def write_registry(check_catalog: bool = True) -> Path:
    src = load_seed()
    errs = validate(src, catalog_rows() if check_catalog else None)
    if errs:
        raise ValueError("; ".join(errs))
    fams = families(src)
    doc = {"generated_by": "python -m pipeline.ingest registry", "split_rule": SPLIT_RULE,
           "splits": assign_splits(fams), "sources": src,
           "blocked": [{"source": "DOHA ISCR / Appeal Board decisions", "url": "https://doha.ogc.osd.mil/",
                        "status": "HTTP 403 on every page from this box (2026-10-25)",
                        "action": "not worked around; replaced by DOE OHA PSH decisions (same adjudicative schema)"}]}
    p = REG_DIR / "sources.yaml"
    write_yaml(p, doc)
    return p


def load_registry() -> dict:
    return yaml.safe_load((REG_DIR / "sources.yaml").read_text())


ACQ = REG_DIR / "acquired.yaml"


def load_acquired() -> dict:
    return yaml.safe_load(ACQ.read_text()) if ACQ.exists() else {}


def save_acquired(d: dict):
    write_yaml(ACQ, d)
