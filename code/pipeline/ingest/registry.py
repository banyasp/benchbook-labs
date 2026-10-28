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
    """Design v2.4.1 §13.5 / brief W4a: every episode of one source document shares that document's family.
    A document is the fetched source; for a regulation fetched as a whole subpart, each CFR section is a separately
    citable document (OGE-2635-204), so its examples share the section's family."""
    if source.get("family"):
        return source["family"]
    if ep.get("section"):                      # e.g. family_prefix OGE + section 2635.204 -> OGE-2635-204
        return f"{source.get('family_prefix', source['id'])}-{ep['section'].replace('.', '-')}"
    return source["id"]


def legacy_families(sources: list[dict]) -> dict[str, str]:
    """2f family (per episode, written into old scenario ids) -> v2.4 document family."""
    return {e["family"]: family_of(s, e) for s in sources for e in s["episodes"] if e.get("family")}


def families(sources: list[dict]) -> list[str]:
    return sorted({family_of(s, e) for s in sources for e in s["episodes"]})


def assign_splits(fams: list[str]) -> dict[str, str]:
    """Deterministic per-family split. Order families by sha256(family); the first is `test`, the second `dev`,
    the rest `train` (needs >= 3 families; with fewer, everything is train and the caller must say so)."""
    order = sorted(set(fams), key=lambda f: hashlib.sha256(f.encode()).hexdigest())
    if len(order) < 3:
        return {f: "train" for f in order}
    return {f: ("test" if i == 0 else "dev" if i == 1 else "train") for i, f in enumerate(order)}


SPLIT_RULE_V1 = ("families sorted by sha256(family id); first -> test, second -> dev, remaining -> train; "
              "fewer than 3 families -> all train. Splits are per family, assigned before any perturbation.")


HELD_OUT_DOMAINS = ("military-operational",)   # brief v2.4 W8b: the whole held-out source domain (all test)
TEST_FRAC, DEV_FRAC, MIN_TEST = 0.2, 0.1, 5

SPLIT_RULE = ("v2 (design v2.4.1 §13.5, brief W4a): family = source document (all its episodes share it); per domain, "
              "families sorted by sha256(family id); the first ~20% go to test (at least 5 when the domain has >= 15 "
              "families, else at least 1 once it has 3), the next ~10% to dev, the rest to train; every family of a "
              f"held-out domain ({', '.join(HELD_OUT_DOMAINS)}) goes to test; pilot imports stay eval-only. "
              "Assigned before any perturbation; derived scenarios inherit their root's split.")


def n_test_dev(n: int) -> tuple[int, int]:
    if n < 3:
        return 0, 0
    nt = max(round(TEST_FRAC * n), MIN_TEST if n >= 15 else 1)
    nd = max(round(DEV_FRAC * n), 1 if n >= 5 else 0)
    return nt, nd


def assign_splits_v2(fam_domain: dict[str, str], held_out: tuple[str, ...] = HELD_OUT_DOMAINS) -> tuple[dict, list]:
    """-> ({family: split}, warnings). fam_domain: family -> domain."""
    out, warn = {}, []
    by_dom: dict[str, list[str]] = {}
    for f, d in fam_domain.items():
        by_dom.setdefault(d, []).append(f)
    for d, fams in sorted(by_dom.items()):
        order = sorted(fams, key=lambda f: hashlib.sha256(f.encode()).hexdigest())
        if d in held_out:
            out.update({f: "test" for f in order})
            continue
        nt, nd = n_test_dev(len(order))
        if nt < MIN_TEST:
            warn.append(f"domain `{d}`: {len(order)} families -> {nt} test (< {MIN_TEST}); add sources")
        out.update({f: "test" if i < nt else "dev" if i < nt + nd else "train" for i, f in enumerate(order)})
    return out, warn


def write_registry(check_catalog: bool = True) -> Path:
    src = load_seed()
    errs = validate(src, catalog_rows() if check_catalog else None)
    if errs:
        raise ValueError("; ".join(errs))
    fam_domain = {family_of(s, e): s["domain"] for s in src for e in s["episodes"]}
    fam_domain.update(natsec_families())
    splits, warnings = assign_splits_v2(fam_domain)
    doc = {"generated_by": "python -m pipeline.ingest registry", "split_rule": SPLIT_RULE,
           "splits": splits, "split_warnings": warnings, "legacy_families": legacy_families(src), "sources": src,
           "blocked": [{"source": "DOHA ISCR / Appeal Board decisions", "url": "https://doha.ogc.osd.mil/",
                        "status": "HTTP 403 on every page from this box (2026-10-25)",
                        "action": "not worked around; replaced by DOE OHA PSH decisions (same adjudicative schema)"}]}
    p = REG_DIR / "sources.yaml"
    write_yaml(p, doc)
    return p


def natsec_families() -> dict[str, str]:
    """W8b held-out sources: family -> domain (all military-operational)."""
    p = Path(__file__).with_name("sources-natsec.seed.yaml")
    if not p.exists():
        return {}
    seed = yaml.safe_load(p.read_text())
    dom = seed.get("defaults", {}).get("held_out_domain", "military-operational")
    return {s["family"]: dom for s in seed["sources"]}


def load_registry() -> dict:
    return yaml.safe_load((REG_DIR / "sources.yaml").read_text())


ACQ = REG_DIR / "acquired.yaml"


def load_acquired() -> dict:
    return yaml.safe_load(ACQ.read_text()) if ACQ.exists() else {}


def save_acquired(d: dict):
    write_yaml(ACQ, d)
