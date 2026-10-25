"""2f store (BUILD-BRIEF-2f §Storage). Leaves data/cases and data/scenarios (2b, Checkpoint 2) untouched.

    data/raw/<sha256>  + <sha256>.meta.json        immutable source bytes
    data/docs/<sha12>.jsonl                        normalized text, one span per line {"span": "src:<sha12>#p3.4", "text": ...}
    data/store/registry/sources.yaml               sources picked for tonight (from context/sources/source-catalog.csv)
    data/store/scenarios/<family>/<id>.yaml        Scenario records
    data/store/pairs/<pair-id>/pair.yaml           PairRecord (+ trace.json, span_map inside the record, solve/)
    data/exports/<version>/{sft,rl,eval}/          projections (regenerable)

Every write of an existing file first copies it to a versions/ folder beside it (never overwrite).
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import yaml

from bench.schema.pipeline import PairRecord, Scenario

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def _keep_version(p: Path):
    if p.exists():
        v = p.parent / "versions"
        v.mkdir(exist_ok=True)
        stem, dot, ext = p.name.rpartition(".")
        shutil.copy2(p, v / f"{stem}.{time.strftime('%Y%m%d-%H%M%S')}.{ext}")


def write_yaml(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    _keep_version(p)
    p.write_text(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, width=120))


def write_json(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    _keep_version(p)
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False))


class Store:
    def __init__(self, data: Path | str = DATA):
        self.data = Path(data)
        self.raw = self.data / "raw"
        self.docs = self.data / "docs"
        self.root = self.data / "store"
        self.exports = self.data / "exports"

    # scenarios
    def scenario_path(self, s: Scenario | str, family: str | None = None) -> Path:
        if isinstance(s, Scenario):
            return self.root / "scenarios" / s.family / f"{s.id}.yaml"
        hits = list((self.root / "scenarios").glob(f"*/{s}.yaml"))
        if not hits:
            raise KeyError(s)
        return hits[0]

    def save_scenario(self, s: Scenario) -> Path:
        Scenario.model_validate(s.dump())          # round-trip check before writing
        p = self.scenario_path(s)
        write_yaml(p, s.dump())
        return p

    def scenario(self, sid: str) -> Scenario:
        return Scenario.load(self.scenario_path(sid))

    def scenarios(self, split: str | None = None, family: str | None = None) -> list[Scenario]:
        out = [Scenario.load(p) for p in sorted((self.root / "scenarios").glob("*/*.yaml"))]
        return [s for s in out if (split is None or s.split == split) and (family is None or s.family == family)]

    # pairs
    def pair_dir(self, pid: str) -> Path:
        return self.root / "pairs" / pid

    def save_pair(self, p: PairRecord) -> Path:
        PairRecord.model_validate(p.dump())
        path = self.pair_dir(p.id) / "pair.yaml"
        write_yaml(path, p.dump())
        return path

    def pair(self, pid: str) -> PairRecord:
        return PairRecord.load(self.pair_dir(pid) / "pair.yaml")

    def pairs(self) -> list[PairRecord]:
        return [PairRecord.load(p) for p in sorted((self.root / "pairs").glob("*/pair.yaml"))]

    # docs
    def doc_spans(self, sha12: str) -> list[dict]:
        return [json.loads(l) for l in (self.docs / f"{sha12}.jsonl").read_text().splitlines() if l.strip()]
