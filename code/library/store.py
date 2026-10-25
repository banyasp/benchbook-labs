"""The on-disk library: cases, equity sets, scenarios + answer keys, manifest.

    data/cases/<FAMILY>/<case id>.case.yaml          e.g. data/cases/INT-301/DR-INT-301@v1.case.yaml
    data/cases/<FAMILY>/versions/                    replaced files, never deleted (<file>.vN-<what>.yaml)
    data/cases/<FAMILY>/_convert/                    raw converter prompts + model output (audit)
    data/cases/MANIFEST.yaml
    data/registry/equities/<set>.yaml
    data/scenarios/<FAMILY>/<scenario id>.scenario.yaml
    data/scenarios/<FAMILY>/<scenario id>.<arm>.key.yaml
"""
from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path

import yaml
from bench.schema import AnswerKey, Case, EquitySet, LiveScenario

REPO = Path(__file__).resolve().parents[2]
_CID = re.compile(r"^(DR-.+)@v(\d+)$")


def sha256_file(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump_yaml(obj) -> str:
    return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, width=120)


def keep_version(path: Path, what: str) -> Path | None:
    """Copy an existing file into the `versions/` folder beside it before it is replaced."""
    path = Path(path)
    if not path.exists():
        return None
    vdir = path.parent / "versions"
    vdir.mkdir(exist_ok=True)
    stem, suffix = path.name.split(".", 1)[0], path.name.split(".", 1)[1]
    n = 1
    while True:
        dest = vdir / f"{stem}.v{n}-{what}.{suffix}"
        if not dest.exists():
            shutil.copy2(path, dest)
            return dest
        n += 1


def write_versioned(path, text: str, what: str) -> Path:
    """Write text to path; if the file exists and differs, keep the old one in versions/ first."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text() == text:
            return path
        keep_version(path, what)
    path.write_text(text)
    return path


class Library:
    def __init__(self, root="data"):
        root = Path(root)
        if not root.is_absolute() and not root.exists():
            root = REPO / root
        self.root = root.resolve()
        self.cases_dir = self.root / "cases"
        self.equities_dir = self.root / "registry" / "equities"
        self.scenarios_dir = self.root / "scenarios"

    # ---- cases
    def case_files(self) -> list[Path]:
        return sorted(self.cases_dir.glob("*/*.case.yaml"))

    def case_path(self, case_id: str) -> Path:
        m = _CID.match(case_id)
        if m:
            hits = list(self.cases_dir.glob(f"*/{case_id}.case.yaml"))
        else:   # latest version
            vs = []
            for p in self.cases_dir.glob(f"*/{case_id}@v*.case.yaml"):
                vs.append((int(_CID.match(p.name[:-len(".case.yaml")]).group(2)), p))
            hits = [max(vs)[1]] if vs else []
        if not hits:
            raise KeyError(f"no case `{case_id}` under {self.cases_dir}")
        return hits[0]

    def case(self, case_id: str) -> Case:
        return Case.load(self.case_path(case_id))

    def case_ids(self) -> list[str]:
        return [p.name[:-len(".case.yaml")] for p in self.case_files()]

    def cases(self) -> list[Case]:
        return [Case.load(p) for p in self.case_files()]

    def save_case(self, case: Case, family: str, what: str = "reconverted") -> Path:
        p = self.cases_dir / family / f"{case.id}.case.yaml"
        write_versioned(p, dump_yaml(case.dump()), what)
        return p

    # ---- equities
    def equities(self, set_id: str) -> EquitySet:
        p = self.equities_dir / f"{set_id}.yaml"
        if not p.exists():
            raise KeyError(f"no equity set `{set_id}` at {p}")
        return EquitySet.model_validate(yaml.safe_load(p.read_text()))

    # ---- scenarios
    def scenario_files(self) -> list[Path]:
        return sorted(self.scenarios_dir.glob("*/*.scenario.yaml"))

    def scenarios(self, family: str | None = None, split: str | None = None) -> list[LiveScenario]:
        out = []
        for p in self.scenario_files():
            s = LiveScenario.load(p)
            if (family is None or s.family == family) and (split is None or s.split == split):
                out.append(s)
        return out

    def scenario(self, scenario_id: str) -> LiveScenario:
        hits = list(self.scenarios_dir.glob(f"*/{scenario_id}.scenario.yaml"))
        if not hits:
            raise KeyError(f"no scenario `{scenario_id}` under {self.scenarios_dir}")
        return LiveScenario.load(hits[0])

    # ---- validation
    def validate(self) -> list[str]:
        """Load everything with the 2a models and cross-check references. Returns problems (empty = clean)."""
        errs: list[str] = []
        cases: dict[str, Case] = {}
        for p in self.case_files():
            try:
                c = Case.load(p)
            except Exception as e:  # noqa: BLE001
                errs.append(f"{p.name}: {str(e)[:400]}")
                continue
            if p.name != f"{c.id}.case.yaml":
                errs.append(f"{p.name}: file name does not match case id {c.id}")
            if p.parent.name != c.library.get("family", p.parent.name):
                errs.append(f"{p.name}: lives in {p.parent.name}/ but library.family is {c.library.get('family')}")
            cases[c.id] = c
        sets: dict[str, EquitySet] = {}
        for p in sorted(self.equities_dir.glob("*.yaml")):
            if p.name.endswith(".meta.yaml"):
                continue
            try:
                sets[p.stem] = EquitySet.model_validate(yaml.safe_load(p.read_text()))
            except Exception as e:  # noqa: BLE001
                errs.append(f"equities/{p.name}: {str(e)[:400]}")
        for s_path in self.scenario_files():
            try:
                s = LiveScenario.load(s_path)
            except Exception as e:  # noqa: BLE001
                errs.append(f"{s_path.name}: {str(e)[:400]}")
                continue
            if s.equities not in sets:
                errs.append(f"{s.id}: equity set `{s.equities}` not found")
            if s.perturbation.source_case not in cases:
                errs.append(f"{s.id}: source_case {s.perturbation.source_case} is not in the library")
            if not (REPO / s.trace).exists():
                errs.append(f"{s.id}: trace {s.trace} does not exist")
            for arm, spec in s.arms.items():
                for cid in spec.served:
                    if cid not in cases:
                        errs.append(f"{s.id}/{arm}: served case {cid} is not in the library")
                try:
                    k = s.answer_key(arm)
                except Exception as e:  # noqa: BLE001
                    errs.append(f"{s.id}/{arm}: key: {str(e)[:400]}")
                    continue
                if k.scenario != s.id or k.arm != arm:
                    errs.append(f"{s.id}/{arm}: key says scenario={k.scenario} arm={k.arm}")
                if (k.served or None) != (spec.served[0] if spec.served else None):
                    errs.append(f"{s.id}/{arm}: key.served {k.served} differs from the scenario's {spec.served}")
                for v in k.via or []:
                    cid, _, item = v.partition("/")
                    c = cases.get(cid)
                    if not c or item not in {w.id for w in c.flip_conditions.would_change}:
                        errs.append(f"{s.id}/{arm}: via {v} is not a would_change item of a library case")
                if k.relation == "flips" and k.via:
                    c = cases.get(k.served or "")
                    if c:
                        thens = {w.id: w.then for w in c.flip_conditions.would_change}
                        want = (k.option_map or {}).get(k.choice)
                        for v in k.via:
                            item = v.partition("/")[2]
                            if want and thens.get(item) and f"{c.id}/{thens[item]}" != want:
                                errs.append(f"{s.id}/{arm}: via {v} says {thens[item]} but the gold choice maps to {want}")
        eqs = sets.get("pilot")
        if eqs:
            for c in cases.values():
                for con in c.considerations:
                    if con.equity not in eqs.ids():
                        errs.append(f"{c.id}/{con.id}: equity `{con.equity}` is not in the pilot equity set")
        return errs

    # ---- manifest
    def write_manifest(self) -> Path:
        rows = []
        for p in self.case_files():
            c = Case.load(p)
            lib = c.library
            rows.append({"id": c.id, "family": lib.get("family"), "file": str(p.relative_to(self.root)),
                         "sha256": sha256_file(p), "status": c.status, "split_hint": lib.get("split_hint"),
                         "source": (lib.get("provenance") or {}).get("source_file"),
                         "options": len(c.options), "choice": c.verdict.choice})
        path = self.cases_dir / "MANIFEST.yaml"
        header = "# Generated by `python -m library convert-cases` / `validate`; do not hand-edit.\n"
        write_versioned(path, header + dump_yaml({"cases": rows}), "manifest")
        return path
