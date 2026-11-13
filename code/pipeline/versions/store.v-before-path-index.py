"""2f store (BUILD-BRIEF-2f §Storage). Leaves data/cases and data/scenarios (2b, Checkpoint 2) untouched.

    data/raw/<sha256>  + <sha256>.meta.json        immutable source bytes
    data/docs/<sha12>.jsonl                        normalized text, one span per line {"span": "src:<sha12>#p3.4", "text": ...}
    data/store/registry/sources.yaml               sources picked for tonight (from context/sources/source-catalog.csv)
    data/store/scenarios/<family>/<id>.yaml        Scenario records
    data/store/traces/<trace-scenario-id>/         TraceRecord: trace.yaml (σ, channels, recommended_option) + trace.json
    data/store/pairs/<pair-id>/pair.yaml           PairRecord (references a trace by trace_ref; solve/ samples)
    data/store/episodes/, data/store/incomplete/   episode finder rejects; incomplete extractions (design §4.2-4.3)
    data/exports/<version>/{sft,rl,eval}/          projections (regenerable)

Every write of an existing file first copies it to a versions/ folder beside it (never overwrite).
"""
from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

import yaml

from bench.schema.pipeline import PairRecord, Scenario, TraceRecord

ROOT = Path(__file__).resolve().parents[2]
INACTIVE_TAGS = {"superseded", "legacy-2f", "rejected"}
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
        """Every pair record on disk, including inactive ones (superseded / legacy-2f / rejected). Pair build only."""
        return [PairRecord.load(p) for p in sorted((self.root / "pairs").glob("*/pair.yaml"))]

    def active_pairs(self) -> list[PairRecord]:
        """Pairs a consumer may use: not tagged superseded, legacy-2f or rejected (those stay on disk, never deleted)."""
        return [p for p in self.pairs() if not INACTIVE_TAGS & set(p.tags)]

    # traces (design §7.1: one per trace scenario; pairs reference, never copy)
    def trace_dir(self, trace_scenario: str) -> Path:
        return self.root / "traces" / trace_scenario

    def save_trace(self, t: TraceRecord, trace_json: dict | None = None) -> Path:
        TraceRecord.model_validate(t.dump())
        d = self.trace_dir(t.trace_scenario)
        if trace_json is not None:
            write_json(d / t.trace, trace_json)
        write_yaml(d / "trace.yaml", t.dump())
        return d

    def trace(self, trace_scenario: str) -> TraceRecord:
        return TraceRecord.load(self.trace_dir(trace_scenario) / "trace.yaml")

    def trace_json(self, trace_scenario: str) -> dict:
        t = self.trace(trace_scenario)
        return json.loads((self.trace_dir(trace_scenario) / t.trace).read_text())

    def has_trace(self, trace_scenario: str) -> bool:
        return (self.trace_dir(trace_scenario) / "trace.yaml").exists()

    def traces(self) -> list[TraceRecord]:
        return [TraceRecord.load(p) for p in sorted((self.root / "traces").glob("*/trace.yaml"))]

    # docs
    def doc_spans(self, sha12: str) -> list[dict]:
        return [json.loads(l) for l in (self.docs / f"{sha12}.jsonl").read_text().splitlines() if l.strip()]
