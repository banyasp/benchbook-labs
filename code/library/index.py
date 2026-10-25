"""Stub structural index (DATA-PIPELINE-DESIGN-v1 section 4): the SQLite schema, filled from the case files.
Similarity search is a stub. Embeddings are not computed; the table exists so the schema is fixed."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from bench.schema import Case

from .store import Library

SCHEMA = """
CREATE TABLE cases (
  id TEXT PRIMARY KEY, family TEXT, version INTEGER, domain TEXT, decider TEXT, agent_role TEXT,
  classification TEXT, status TEXT, split TEXT, choice TEXT, choice_move TEXT, basis TEXT, signature TEXT);
CREATE TABLE options (
  case_id TEXT, id TEXT, move TEXT, irreversible INTEGER, reveals_asset INTEGER, hands_to TEXT,
  is_choice INTEGER, PRIMARY KEY (case_id, id));
CREATE TABLE facts (
  case_id TEXT, id TEXT, kind TEXT, status TEXT, span_ref TEXT, PRIMARY KEY (case_id, id));
CREATE TABLE considerations (
  case_id TEXT, id TEXT, equity TEXT, favors TEXT, favors_moves TEXT, weight TEXT, decisive INTEGER,
  pulls TEXT, rules_out TEXT, facts TEXT, PRIMARY KEY (case_id, id));
CREATE TABLE flip_conditions (
  case_id TEXT, id TEXT, kind TEXT, then_option TEXT, then_move TEXT, equity_touched TEXT,
  PRIMARY KEY (case_id, id));
CREATE TABLE equities (set_id TEXT, id TEXT, gloss TEXT, PRIMARY KEY (set_id, id));
CREATE TABLE embeddings (case_id TEXT, item TEXT, field TEXT, model TEXT, vector BLOB, PRIMARY KEY (case_id, item, field));
"""


def signature(c: Case) -> dict:
    """The structural signature (design section 4): tension, decisive considerations, move structure, authority shape.
    Facts are deliberately absent: retrieval matches on structure, not domain facts."""
    choice = c.verdict.choice
    side: dict[str, list] = {"for_choice": [], "against_choice": []}
    for k in c.considerations:
        side["for_choice" if choice in k.favors else "against_choice"].append(
            {"equity": k.equity, "weight": k.weight, "decisive": k.id in c.verdict.decisive})
    return {
        "tension": side,
        "decisive": [{"equity": k.equity, "weight": k.weight} for k in c.considerations if k.id in c.verdict.decisive],
        "move_structure": {o: {"move": v.move, "irreversible": bool(v.irreversible)} for o, v in c.options.items()},
        "won": c.options[choice].move,
        "authority": {"agent_role": c.agent_role, "decider": c.decider},
    }


def build_index(lib: Library, path) -> dict:
    """(Re)build the SQLite index at `path` from the case files. Returns row counts."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()      # the index is derived and rebuilt from the files, never a source of truth
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    for c in lib.cases():
        fam = c.library.get("family")
        ver = int(c.id.rpartition("@v")[2])
        mv = {o: v.move for o, v in c.options.items()}
        db.execute("INSERT INTO cases VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   (c.id, fam, ver, c.library.get("domain"), c.decider, c.agent_role, c.library.get("classification"),
                    c.status, c.library.get("split_hint"), c.verdict.choice, mv[c.verdict.choice], c.verdict.basis,
                    json.dumps(signature(c))))
        for o, v in c.options.items():
            db.execute("INSERT INTO options VALUES (?,?,?,?,?,?,?)",
                       (c.id, o, v.move, int(bool(v.irreversible)), None, v.to, int(o == c.verdict.choice)))
        for f in c.facts:
            db.execute("INSERT INTO facts VALUES (?,?,?,?,?)", (c.id, f.id, f.kind, f.status, None))
        for k in c.considerations:
            db.execute("INSERT INTO considerations VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (c.id, k.id, k.equity, json.dumps(k.favors), json.dumps([mv[o] for o in k.favors]), k.weight,
                        int(k.id in c.verdict.decisive), "toward" if c.verdict.choice in k.favors else "against",
                        json.dumps(k.rules_out or []), json.dumps(k.facts)))
        fc = c.flip_conditions
        for w in fc.would_change:
            db.execute("INSERT INTO flip_conditions VALUES (?,?,?,?,?,?)", (c.id, w.id, "would_change", w.then, mv[w.then], None))
        for w in fc.would_not_change:
            db.execute("INSERT INTO flip_conditions VALUES (?,?,?,?,?,?)", (c.id, w.id, "would_not_change", None, None, None))
        for w in fc.watch_for:
            db.execute("INSERT INTO flip_conditions VALUES (?,?,?,?,?,?)",
                       (c.id, w.id, "watch_for", ",".join(w.favors), None, None))
    for p in sorted(lib.equities_dir.glob("*.yaml")):
        if p.name.endswith(".meta.yaml"):
            continue
        es = lib.equities(p.stem)
        for e in es.equities:
            db.execute("INSERT INTO equities VALUES (?,?,?)", (p.stem, e.id, e.gloss))
    db.commit()
    counts = {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("cases", "options", "facts", "considerations", "flip_conditions", "equities", "embeddings")}
    db.close()
    return counts


def search(index_path, query_signature: dict, k: int = 1) -> list[str]:
    """Structural similarity search over the index. Stub."""
    raise NotImplementedError("similarity search is a stub (design section 4: weighted matching + embedding tiebreak)")
