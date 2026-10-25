"""Pilot live scenarios (v2.6 *.live.yaml + rendered trace) -> LiveScenario + one AnswerKey per arm. Deterministic, no LLM.

Arms
  none       gold = the live gold choice; no relation, nothing served.
  relevant   served = the reference case (converted); gold choice + relation from the live file; for `flips`, `via` is the
             converted case's flip id for the boundary the variant was built on (case.library.boundary_map).
  augmented  served = the `-r1` revised card listed in `revised_cards`; gold = that entry's choice/relation.
  decoy      served = the first card in `decoys`; gold choice unchanged, relation not_governed, governs false.

Gold option set = the live file's options as LIVE-O1.. in the live file's order, source_id = the v2.6 letter.
Option order is the live file's (A, B, C...): nothing here shuffles it. See cues() for the position/length checks.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from bench.schema import AnswerKey, GoldOption, LiveScenario, Perturbation, Touched

from ..store import REPO, Library, dump_yaml, sha256_file, write_versioned
from .cases import case_id_for

B = "data/draft/B001"
LIVE_FILES = (
    [f"{B}/{fam}/{fam}-v0{n}.live.yaml" for fam in ("INT-301", "REL-301", "OVS-301") for n in (1, 2, 3, 4)]
    + ["examples-v21/AUT-001/AUT-101.live.yaml", "examples-v21/INT-103/INT-103-v01.live.yaml",
       "examples-v21/AGT-201/AGT-201-v01.live.yaml"]
)
# Live files that exist but have no rendered trace (so no scenario): listed for the report.
NO_TRACE = ["examples-v21/AUT-001/AUT-001-v01.live.yaml", "examples-v21/INT-103/INT-103-v02.live.yaml"]
# A flip whose `boundary:` is null in the live file. AUT-101: gold.why says two of AUT-001's would_change items seem to
# hold and the 'likely alive and reachable -> ask' item decides (gold C = the ask-type option). Index 2. Inferred, flagged.
VIA_OVERRIDE = {"AUT-101": ("would_change", 2)}
HERE_TO_CHANGE = {"missing": "removed", "stronger": "revised", "weaker": "revised", "same": "same"}


def _words(s) -> int:
    return len(str(s).split())


def _trace_path(live_path: Path) -> Path:
    return live_path.with_name(live_path.name.replace(".live.yaml", ".trace.json"))


def _fam_dirs(ref: str) -> str:
    return ref


def build_one(lib: Library, live_rel: str) -> tuple[LiveScenario, dict[str, AnswerKey], list[str]]:
    live_path = REPO / live_rel
    live = yaml.safe_load(live_path.read_text())
    notes: list[str] = []
    trace = _trace_path(live_path)
    if not trace.exists() or "messages" not in json.loads(trace.read_text()):
        raise FileNotFoundError(f"{live_rel}: no rendered trace at {trace}")
    sid, ref = live["id"], live["reference"]
    gold = live["gold"]
    letters = list(live["scenario"]["options"])
    live_ids = {l: f"LIVE-O{i + 1}" for i, l in enumerate(letters)}
    options = {live_ids[l]: GoldOption(do=" ".join(o["do"].split()), move=o["move"], irreversible=o.get("irreversible"), source_id=l)
               for l, o in live["scenario"]["options"].items()}
    ref_case_id = case_id_for(ref)
    ref_case = lib.case(ref_case_id)
    src2opt = {v: k for k, v in ref_case.library["source_ids"].items()}      # letter -> O#
    bmap = ref_case.library["boundary_map"]

    def option_map(case_id: str) -> dict[str, str | None]:
        out = {}
        for l, lid in live_ids.items():
            m = (gold.get("option_map") or {}).get(l)
            out[lid] = f"{case_id}/{src2opt[m]}" if m else None
        return out

    def key(arm, *, served, choice_letter, acceptable_letters, relation, via=None, with_map=False, extra=None):
        return AnswerKey(
            scenario=sid, arm=arm, served=served, options=options, choice=live_ids[choice_letter],
            acceptable=[live_ids[x] for x in acceptable_letters if x != choice_letter],
            relation=relation, via=via, option_map=option_map(served) if with_map else None,
            governs=None if arm == "none" else (relation != "not_governed"),
            provenance={"source_file": live_rel, "source_sha256": sha256_file(live_path), "method": "deterministic from the live gold",
                        "gold_why": " ".join(str(gold.get("why", "")).split()), **(extra or {})})

    keys: dict[str, AnswerKey] = {}
    accept = gold.get("acceptable") or [gold["choice"]]
    keys["none"] = key("none", served=None, choice_letter=gold["choice"], acceptable_letters=accept, relation=None)
    # relevant
    via, via_note = None, None
    if gold["relation"] == "flips":
        if sid in VIA_OVERRIDE:
            kind, idx = VIA_OVERRIDE[sid]
            via_note = f"boundary is null in the live file; via inferred as {kind}[{idx}] from gold.why (flag for Peter)"
            notes.append(via_note)
        else:
            kind, idx = "would_change", live["boundary"]
        if idx is None:
            raise ValueError(f"{sid}: flips without a boundary")
        via = [f"{ref_case_id}/{bmap[f'{kind}[{idx}]']}"]
    keys["relevant"] = key("relevant", served=ref_case_id, choice_letter=gold["choice"], acceptable_letters=accept,
                           relation=gold["relation"], via=via, with_map=True, extra={"via_note": via_note} if via_note else None)
    arms = {"none": [], "relevant": [ref_case_id]}
    # augmented
    for rc in live.get("revised_cards") or []:
        rid = case_id_for(rc["served"])
        lib.case(rid)   # must exist
        keys["augmented"] = key("augmented", served=rid, choice_letter=rc["choice"], acceptable_letters=[rc["choice"]],
                                relation=rc["relation"], with_map=True)
        arms["augmented"] = [rid]
        break
    if len(live.get("revised_cards") or []) > 1:
        notes.append("more than one revised card listed; only the first is used")
    # decoy
    if live.get("decoys"):
        did = case_id_for(live["decoys"][0])
        lib.case(did)
        keys["decoy"] = key("decoy", served=did, choice_letter=gold["choice"], acceptable_letters=accept, relation="not_governed")
        arms["decoy"] = [did]
        if len(live["decoys"]) > 1:
            notes.append("more than one decoy listed; only the first is used")
    # perturbation
    variant, boundary = live["variant"], live.get("boundary")
    bkind = {"flip": "would_change", "trap": "would_not_change"}.get(variant)
    operator = {"restyle": "restyle: same considerations in new surface terms", "stronger": "strengthen the pull toward the reference answer",
                "cross": "cross-domain transfer", "novel": "novel situation"}.get(variant)
    if bkind and boundary is not None:
        operator = f"{variant} built on {ref_case_id}/{bmap[f'{bkind}[{boundary}]']} (v2.6 {bkind}[{boundary}])"
    elif sid in VIA_OVERRIDE:
        operator = f"cross-domain flip; {via_note}"
    touched = []
    new_n = 0
    c_of = {old: new for new, old in ref_case.library["source_consideration_ids"].items()}
    for p in gold.get("planted") or []:
        if p["ref"] == "new":
            new_n += 1
            touched.append(Touched(item=f"LIVE-new{new_n}", item_kind="consideration", change="added",
                                   note=f"favors {p.get('favors')} value {p.get('value')}: {' '.join(str(p.get('what', '')).split())}"))
        else:
            change = HERE_TO_CHANGE[p["here"]]
            if variant == "restyle" and p["here"] == "same":
                change = "restyled"
            touched.append(Touched(item=f"{ref_case_id}/{c_of[p['ref']]}", item_kind="consideration", change=change,
                                   note=f"{p['here']}: {' '.join(str(p.get('what', '')).split())}"))
    pert = Perturbation(variant=variant, operator=operator, source_case=ref_case_id, touched=touched,
                        domain_shift=(variant == "cross"), notes=None)
    # shortcut cue flags for this scenario
    lens = {l: _words(o["do"]) for l, o in live["scenario"]["options"].items()}
    cue = {"gold_position": letters.index(gold["choice"]) + 1, "n_options": len(letters),
           "gold_is_longest": lens[gold["choice"]] == max(lens.values()), "gold_move": live["scenario"]["options"][gold["choice"]]["move"],
           "option_words": lens}
    family = ref
    spec_arms = {}
    for arm, served in arms.items():
        spec_arms[arm] = {"served": served, "key": f"{sid}.{arm}.key.yaml"}
    sc = LiveScenario.model_validate({
        "id": sid, "family": family, "split": "pilot", "domain": ref_case.library.get("domain"),
        "trace": str(trace.relative_to(REPO)), "equities": "pilot", "arms": spec_arms,
        "perturbation": pert.model_dump(exclude_none=True),
        "provenance": {"source_file": live_rel, "source_sha256": sha256_file(live_path), "reference": ref, "built_by": "library.convert.scenarios",
                       "split_hint": "eval-only (Claude-drafted live scenario)",
                       "option_order": "the live file's own order: A, B, C... = LIVE-O1, LIVE-O2, ...; never shuffled here",
                       "cues": cue, "notes": notes},
    })
    return sc, keys, notes


def build_all(lib: Library, files: list[str] | None = None) -> list[str]:
    lines, cues, table = [], {}, []
    for rel in files or LIVE_FILES:
        sc, keys, notes = build_one(lib, rel)
        d = lib.scenarios_dir / sc.family
        d.mkdir(parents=True, exist_ok=True)
        for arm, k in keys.items():
            write_versioned(d / f"{sc.id}.{arm}.key.yaml", dump_yaml(k.model_dump(by_alias=True, exclude_none=True)), "rebuilt")
        write_versioned(d / f"{sc.id}.scenario.yaml", dump_yaml(sc.model_dump(by_alias=True, exclude_none=True)), "rebuilt")
        cues[sc.id] = sc.provenance["cues"]
        for arm, k in keys.items():
            table.append((sc.id, arm, k.choice, k.options[k.choice].source_id, k.relation, k.via))
        lines.append(f"{sc.id:16} arms={','.join(keys)} notes={notes}")
    for rel in NO_TRACE:
        lines.append(f"SKIPPED (no rendered trace): {rel}")
    write_versioned(lib.scenarios_dir / "CUES.yaml", dump_yaml(summarize_cues(cues)), "rebuilt")
    lines.append("scenario | arm | gold | letter | relation | via")
    lines += [" | ".join(str(x) for x in row) for row in table]
    return lines


def summarize_cues(cues: dict) -> dict:
    n = len(cues)
    pos: dict[int, int] = {}
    for c in cues.values():
        pos[c["gold_position"]] = pos.get(c["gold_position"], 0) + 1
    moves: dict[str, int] = {}
    for c in cues.values():
        moves[c["gold_move"]] = moves.get(c["gold_move"], 0) + 1
    chance_longest = sum(1 / c["n_options"] for c in cues.values()) / n if n else None
    return {"n_scenarios": n, "gold_position_counts": pos, "gold_move_counts": moves,
            "gold_is_longest_option": sum(c["gold_is_longest"] for c in cues.values()), "longest_expected_by_chance": chance_longest,
            "per_scenario": cues,
            "note": "Computed on the live files' own option order and text. Position 1 = option A."}
