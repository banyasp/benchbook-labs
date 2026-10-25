"""The `pilot` equity set: the 28 v2.6 values (DATAGEN-SPEC section 2 / mvp.py VALUES) with glosses written by the
converter role. The 5 PDF glosses are kept verbatim. Status lives in a sidecar because 2a's EquitySet forbids extra keys."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
from pathlib import Path
from typing import Callable

import yaml
from bench.schema import EquitySet

from ..store import REPO, Library, dump_yaml, write_versioned
from .cases import _norm

PROMPT_PATH = Path(__file__).parent / "prompts" / "equity.v1.md"

VALUES = [   # DATAGEN-SPEC section 2 order; identical to ideas/schema-mvp-2026-09-30/code/mvp.py VALUES
    "civilian_life", "own_force_life", "duty_to_individual", "hors_de_combat", "humanitarian_access", "mission_effect",
    "tempo", "source_protection", "partner_relationship", "complicity_risk", "usp_privacy", "protected_activity",
    "oversight_candor", "record_integrity", "lawful_authority", "chain_of_command", "analytic_integrity",
    "escalation_control", "third_party_harm", "critical_services", "due_process", "norm_reciprocity",
    "institutional_credibility", "classification_integrity", "public_transparency", "vendor_constraint",
    "control_integrity", "resource_stewardship",
]
PDF_GLOSSES = {
    "civilian_life": "The lives and safety of people who are not combatants, including people in distress at sea.",
    "mission_effect": "Whether the assigned mission achieves the purpose it was given.",
    "source_protection": "Keeping sources, methods and platforms unknown to an adversary so they keep working.",
    "lawful_authority": "Acting within law, orders and the delegation that grants the agent its authority.",
    "resource_stewardship": "Not wasting or losing scarce assets, including the agent's own platform.",
}


def _notes(lib: Library) -> dict[str, list[str]]:
    notes: dict[str, list[str]] = {v: [] for v in VALUES}
    for c in lib.cases():
        for v, n in (c.library.get("value_notes") or {}).items():
            if v in notes and len(notes[v]) < 3:
                notes[v].append(n)
    return notes


def build_pilot_equities(lib: Library, *, llm: Callable | None = None, force: bool = False, today: str | None = None) -> Path:
    path = lib.equities_dir / "pilot.yaml"
    if path.exists() and not force:
        return path
    if llm is None:
        from bench.models import complete
        llm = lambda m: complete("converter", m, stage="equity-gloss")   # noqa: E731
    model_id = None
    try:
        from bench.models import role
        model_id = role("converter").model
    except Exception:  # noqa: BLE001
        pass
    text = re.sub(r"<!--.*?-->", "", PROMPT_PATH.read_text(), flags=re.S)
    _, _, rest = text.partition("# SYSTEM")
    system, _, user = rest.partition("# USER")
    payload = json.dumps({v: n for v, n in _notes(lib).items()}, indent=1, ensure_ascii=False)
    messages = [{"role": "system", "content": system.strip()}, {"role": "user", "content": user.strip().replace("{{PAYLOAD}}", payload)}]
    audit = lib.equities_dir / "_convert"
    audit.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    glosses: dict = {}
    for attempt in range(1, 5):
        raw = llm(messages)
        (audit / f"pilot.{stamp}.attempt{attempt}.response.txt").write_text(raw)
        try:
            t = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
            glosses = json.loads(t[t.find("{"): t.rfind("}") + 1])
            missing = [v for v in VALUES if not str(glosses.get(v, "")).strip()]
            if missing:
                raise ValueError(f"missing glosses for {missing}")
            break
        except Exception as e:  # noqa: BLE001
            messages = messages + [{"role": "assistant", "content": raw},
                                   {"role": "user", "content": f"Not usable: {str(e)[:300]}. Return the corrected full JSON object only."}]
    else:
        raise RuntimeError("the converter did not return glosses for all 28 values in 4 attempts")
    eq = [{"id": v, "gloss": PDF_GLOSSES.get(v) or _norm(glosses[v])} for v in VALUES]
    es = EquitySet.model_validate({"id": "pilot", "equities": eq})
    header = ("# status: needs_review\n# The 28 v2.6 values as an equity set. 5 glosses are the PDF's (p. 11); the other 23 were written by the\n"
              "# converter role (gpt-oss-120b) from the value names and short notes from the pilot cases. Peter to review.\n"
              "# See pilot.meta.yaml (EquitySet forbids extra keys, so status lives beside it).\n")
    write_versioned(path, header + dump_yaml(es.model_dump()), "glosses")
    meta = {"status": "needs_review", "converter_model": model_id, "prompt": "equity.v1",
            "prompt_sha256": hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest(),
            "generated_on": today or _dt.date.today().isoformat(), "pdf_glosses": sorted(PDF_GLOSSES),
            "note": "partner_relationship etc. follow the v2.6 vocabulary; PDF reconciliation A6 is open with Peter."}
    write_versioned(lib.equities_dir / "pilot.meta.yaml", dump_yaml(meta), "meta")
    return path
