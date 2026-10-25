"""v2.6 reference card -> PDF v0.4 `Case` (LLM-assisted, validated).

Deterministic (Python): ids (A-D -> O1.., c1.. -> C1.., boundaries -> flip1/noflip1/watch1), options, verdict, each
consideration's equity (= v2.6 `value`), favors, weight, bar/rules_out, why; flip conditions; lesson, limits; the
`library` block (source map, boundary map, provenance, caveats).
LLM (role `converter`, gpt-oss-120b on Bedrock): the facts list, which facts each consideration rests on, and the
reasoning prose in the PDF's field names. Output is parsed, validated with `Case.model_validate`, and on failure the
errors go back to the model (max 3 retries). Prompt: library/convert/prompts/case.v1.md. Every raw prompt and reply is
kept under data/cases/<FAMILY>/_convert/.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml
from bench.schema import Case

from ..store import REPO, Library, dump_yaml, sha256_file

PROMPT_VERSION = "case.v1"
PROMPT_PATH = Path(__file__).parent / "prompts" / f"{PROMPT_VERSION}.md"
MAX_RETRIES = 3

# source id -> (card path relative to repo, family dir, domain)
B = "data/draft/B001"
SOURCES: dict[str, dict] = {
    "INT-301": {"path": f"{B}/INT-301/INT-301.reference.yaml", "family": "INT-301", "domain": "military intelligence oversight"},
    "INT-301-r1": {"path": f"{B}/INT-301/INT-301-r1.reference.yaml", "family": "INT-301", "domain": "military intelligence oversight"},
    "REL-301": {"path": f"{B}/REL-301/REL-301.reference.yaml", "family": "REL-301", "domain": "foreign disclosure to partners"},
    "REL-301-r1": {"path": f"{B}/REL-301/REL-301-r1.reference.yaml", "family": "REL-301", "domain": "foreign disclosure to partners"},
    "OVS-301": {"path": f"{B}/OVS-301/OVS-301.reference.yaml", "family": "OVS-301", "domain": "oversight and records"},
    "OVS-301-r1": {"path": f"{B}/OVS-301/OVS-301-r1.reference.yaml", "family": "OVS-301", "domain": "oversight and records"},
    "AUT-001": {"path": "examples-v21/AUT-001/AUT-001.reference.yaml", "family": "AUT-001", "domain": "maritime autonomy"},
    "AUT-001-r1": {"path": "examples-v21/AUT-001/AUT-001-r1.reference.yaml", "family": "AUT-001", "domain": "maritime autonomy"},
    "INT-103": {"path": "examples-v21/INT-103/INT-103.reference.yaml", "family": "INT-103", "domain": "counterterrorism analytics"},
    "AGT-201": {"path": "examples-v21/AGT-201/AGT-201.reference.yaml", "family": "AGT-201", "domain": "agent security (injected instructions)"},
}
ROLE_MAP = {"decide": "decide", "execute": "execute", "recommend": "advise", "none": "advise"}


def case_id_for(source_id: str, version: int = 1) -> str:
    return f"DR-{source_id}@v{version}"


def _collapse(s) -> str:
    return " ".join(str(s).split())


_TYPO = str.maketrans({"\u2011": "-", "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"', "\u00a0": " ", "\u202f": " "})


def _norm(s) -> str:
    """Model output sometimes swaps in typographic characters the source does not use."""
    return _collapse(str(s).translate(_TYPO))


class ConversionError(Exception):
    pass


@dataclass
class Conversion:
    source_id: str
    case: Case | None = None
    path: Path | None = None
    attempts: int = 0
    errors: list[str] = field(default_factory=list)      # one entry per failed attempt
    ok: bool = False


# ---------------------------------------------------------------------------------------------------------------
# deterministic part
# ---------------------------------------------------------------------------------------------------------------
@dataclass
class Skeleton:
    data: dict                      # case dict without facts / considerations' facts / reasoning
    letter_to_opt: dict[str, str]
    old_to_new: dict[str, str]      # c1 -> C1
    boundary_map: dict[str, str]
    caveats: list[str]
    flip_ids: list[str]
    llm_card: dict                  # what the model sees


def _refit(text: str, letter_to_opt: dict[str, str], old_to_new: dict[str, str], boundary_ids: dict[str, str]) -> str:
    """Rewrite leftover v2.6 references in prose: 'option B' -> 'option {O2}', 'c3' -> '{C3}'."""
    t = _collapse(text)
    t = re.sub(r"\b([Oo]ption)s? ([A-Z])\b", lambda m: f"{m.group(1)} {{{letter_to_opt[m.group(2)]}}}" if m.group(2) in letter_to_opt else m.group(0), t)
    t = re.sub(r"\bc(\d+)\b", lambda m: f"{{{old_to_new[m.group(0)]}}}" if m.group(0) in old_to_new else m.group(0), t)
    return t


def skeleton(card: dict) -> Skeleton:
    sc, res = card["scenario"], card["resolution"]
    letters = list(sc["options"])
    letter_to_opt = {l: f"O{i + 1}" for i, l in enumerate(letters)}
    cons = res["considerations"]
    old_to_new = {c["id"]: f"C{i + 1}" for i, c in enumerate(cons)}
    caveats: list[str] = []
    options = {}
    for l, o in sc["options"].items():
        d = {"do": _collapse(o["do"]), "move": o["move"]}
        if o.get("irreversible") is not None:
            d["irreversible"] = bool(o["irreversible"])
        if o.get("to"):
            d["to"] = _collapse(o["to"])
        options[letter_to_opt[l]] = d
    ask_opts = [oid for oid, o in options.items() if o["move"] == "ask"]
    choice = letter_to_opt[res["choice"]]
    fb = res["boundaries"]
    rp = lambda t: _refit(t, letter_to_opt, old_to_new, {})   # noqa: E731
    boundary_map: dict[str, str] = {}
    wc, wnc, wf = [], [], []
    for i, w in enumerate(fb["would_change"]):
        then = w["then"]
        if then in letter_to_opt:
            tid = letter_to_opt[then]
        elif then == "ask" and len(ask_opts) == 1:
            tid = ask_opts[0]
        else:
            # v2.6 allowed `then: ask` even when no option asks; the PDF's then must be an option.
            tid = next((o for o in options if o != choice), choice)
            caveats.append(f"flip{i + 1}: v2.6 said then: {then} but the card has no single ask option; mapped to {tid} "
                           f"({options[tid]['do']}). Converter's choice; check.")
        wc.append({"id": f"flip{i + 1}", "if": _collapse(w["if"]), "then": tid, "why": rp(w["why"])})
        boundary_map[f"would_change[{i}]"] = f"flip{i + 1}"
    for i, w in enumerate(fb.get("would_not_change") or []):
        wnc.append({"id": f"noflip{i + 1}", "if": _collapse(w["if"]), "why": rp(w["why"])})
        boundary_map[f"would_not_change[{i}]"] = f"noflip{i + 1}"
    for i, w in enumerate(fb.get("watch_for") or []):
        wf.append({"id": f"watch{i + 1}", "what": _collapse(w["what"]), "favors": [letter_to_opt[x] for x in w["favors"]],
                   "why": rp(w["why"])})
        boundary_map[f"watch_for[{i}]"] = f"watch{i + 1}"
    considerations = []
    for c in cons:
        d = {"id": old_to_new[c["id"]], "facts": [], "equity": c["value"], "favors": [letter_to_opt[x] for x in c["favors"]],
             "weight": c["weight"], "why": rp(c["why"])}
        if c.get("rules_out"):
            d["rules_out"] = [letter_to_opt[x] for x in c["rules_out"]]
        considerations.append(d)
    role = sc["agent_role"]
    if ROLE_MAP[role] != role:
        caveats.append(f"agent_role `{role}` (v2.6) mapped to `{ROLE_MAP[role]}` (PDF vocabulary decide|execute|advise).")
    if any(c["weight"] == "bar" for c in cons):
        caveats.append("weight `bar` kept from v2.6; the PDF shows only strong|weak (2a allows bar; Peter to confirm).")
    j = card["resolution"]["judgment"]
    data = {
        "id": None, "title": card["title"], "status": "needs_review", "setting": _collapse(sc["setting"]),
        "decider": _collapse(sc["decider"]), "agent": _collapse(sc["agent"]), "agent_role": ROLE_MAP[role],
        "situation": _collapse(sc["situation"]), "question": _collapse(sc["question"]), "options": options,
        "considerations": considerations,
        "verdict": {"choice": choice, "basis": res["basis"], "decisive": [old_to_new[x] for x in res["decisive"]]},
        "flip_conditions": {"would_change": wc, "would_not_change": wnc, "watch_for": wf},
        "lesson": rp(res["lesson"]), "limits": rp(res["limits"]),
    }
    tw = j["tempting_wrong"]
    llm_card = {
        "setting": data["setting"], "decider": data["decider"], "agent": data["agent"], "agent_role": data["agent_role"],
        "situation": data["situation"], "question": data["question"], "options": options,
        "considerations": [{"id": d["id"], "was": c["id"], "fact": _collapse(c["fact"]), "equity": d["equity"], "favors": d["favors"],
                            "weight": d["weight"], "why": d["why"]} for d, c in zip(considerations, cons)],
        "verdict": data["verdict"], "flip_conditions": data["flip_conditions"],
        "judgment": {k: (_collapse(j[k]) if k in j else None) for k in ("read", "weighing", "tradecraft", "uncertainty", "handoff")}
                    | {"tempting_wrong": {"option": letter_to_opt[tw["option"]], "pull": _collapse(tw["pull"]), "why_wrong": _collapse(tw["why_wrong"])},
                       "rejected": {letter_to_opt[k]: _collapse(v) for k, v in (j.get("rejected") or {}).items()}},
        "letter_to_option": letter_to_opt, "old_to_new": old_to_new,
    }
    return Skeleton(data, letter_to_opt, old_to_new, boundary_map, caveats, [w["id"] for w in wc], llm_card)


# ---------------------------------------------------------------------------------------------------------------
# LLM part
# ---------------------------------------------------------------------------------------------------------------
def load_prompt() -> tuple[str, str]:
    text = PROMPT_PATH.read_text()
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    _, _, rest = text.partition("# SYSTEM")
    system, _, user = rest.partition("# USER")
    return system.strip(), user.strip()


def parse_json(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    a, b = t.find("{"), t.rfind("}")
    if a < 0 or b < a:
        raise ValueError("reply contains no JSON object")
    return json.loads(t[a:b + 1])


def assemble(sk: Skeleton, out: dict) -> dict:
    """Skeleton + model output -> case dict (not yet validated)."""
    d = json.loads(json.dumps(sk.data))     # deep copy
    facts = out.get("facts")
    if not isinstance(facts, list) or not facts:
        raise ValueError("`facts` must be a non-empty list")
    d["facts"] = [{"id": f.get("id"), "kind": f.get("kind"), "status": f.get("status"), "fact": _norm(f.get("fact", ""))}
                  for f in facts]
    cf = out.get("consideration_facts") or {}
    for c in d["considerations"]:
        if c["id"] not in cf or not cf[c["id"]]:
            raise ValueError(f"`consideration_facts` has no facts for {c['id']}")
        c["facts"] = list(cf[c["id"]])
    r = out.get("reasoning") or {}
    missing = [k for k in ("read", "weighing", "tradecraft", "uncertainty", "handoff", "tempting_wrong") if not r.get(k)]
    if missing:
        raise ValueError(f"`reasoning` is missing {missing}")
    rp = lambda t: _refit(_norm(t), sk.letter_to_opt, sk.old_to_new, {})   # noqa: E731
    tw = r["tempting_wrong"]
    d["reasoning"] = {
        "read": rp(r["read"]), "weighing": rp(r["weighing"]), "tradecraft": rp(r["tradecraft"]),
        "uncertainty": rp(r["uncertainty"]), "handoff": rp(r["handoff"]),
        "tempting_wrong": {"option": sk.llm_card["judgment"]["tempting_wrong"]["option"], "pull": rp(tw["pull"]),
                           "why_wrong": rp(tw["why_wrong"])},
        "rejected": {k: rp(v) for k, v in (r.get("rejected") or {}).items()},
    }
    return d


def extra_checks(case: Case, source_text: str) -> list[str]:
    errs = []
    used = {f for c in case.considerations for f in c.facts}
    unused = [f.id for f in case.facts if f.id not in used]
    if len(unused) > max(2, len(case.facts) // 2):
        errs.append(f"facts {unused} support no consideration; attach each fact to the considerations it bears on")
    ids = [f.id for f in case.facts]
    if ids != [f"F{i + 1}" for i in range(len(ids))]:
        errs.append("fact ids must run F1, F2, ... in order without gaps")
    n_src = source_text.count("[UNVERIFIED]")
    n_out = case.model_dump_json(exclude={"library"}).count("[UNVERIFIED]")
    if n_src and n_out < n_src:
        errs.append(f"the card text has {n_src} [UNVERIFIED] mark(s) in the situation/judgment and the output keeps {n_out}; keep them word for word")
    return errs


def _default_llm(messages, **kw):
    from bench.models import complete
    return complete("converter", messages, stage="convert-case", **kw)


def convert_card(source_id: str, lib: Library, *, llm: Callable | None = None, force: bool = False,
                 model_id: str | None = None, today: str | None = None) -> Conversion:
    spec = SOURCES[source_id]
    src_path = REPO / spec["path"]
    card = yaml.safe_load(src_path.read_text())
    cid = case_id_for(source_id)
    out_path = lib.cases_dir / spec["family"] / f"{cid}.case.yaml"
    res = Conversion(source_id)
    if out_path.exists() and not force:
        res.case, res.path, res.ok = Case.load(out_path), out_path, True
        return res
    llm = llm or _default_llm
    if model_id is None:
        from bench.models import role
        model_id = role("converter").model
    sk = skeleton(card)
    system, user_t = load_prompt()
    payload = json.dumps({"card": sk.llm_card}, ensure_ascii=False, indent=1)
    user = user_t.replace("{{PAYLOAD}}", payload)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    audit = lib.cases_dir / spec["family"] / "_convert"
    audit.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    src_for_marks = " ".join([sk.data["situation"]] + [str(v) for v in card["resolution"]["judgment"].values()])
    case_dict, out = None, {}
    for attempt in range(1, MAX_RETRIES + 2):
        res.attempts = attempt
        (audit / f"{source_id}.{stamp}.attempt{attempt}.prompt.json").write_text(json.dumps(messages, indent=1, ensure_ascii=False))
        raw = llm(messages)
        (audit / f"{source_id}.{stamp}.attempt{attempt}.response.txt").write_text(raw)
        try:
            out = parse_json(raw)
            case_dict = assemble(sk, out)
            case_dict["id"] = cid
            case_dict["library"] = _library_block(sk, out, card, spec, source_id, src_path, model_id, attempt, today)
            case = Case.model_validate(case_dict)
            errs = extra_checks(case, src_for_marks)
            if errs:
                raise ValueError("; ".join(errs))
            res.case, res.ok = case, True
            break
        except Exception as e:  # noqa: BLE001  (json, assemble, pydantic, extra checks)
            msg = str(e)[:1500]
            res.errors.append(msg)
            messages = messages + [{"role": "assistant", "content": raw},
                                   {"role": "user", "content": "Your JSON did not validate:\n" + msg +
                                    "\nReturn the corrected full JSON object only."}]
    if not res.ok:
        return res
    res.path = lib.save_case(res.case, spec["family"], what="reconverted")
    return res


def _library_block(sk: Skeleton, out: dict, card: dict, spec: dict, source_id: str, src_path: Path, model_id: str,
                   attempts: int, today: str | None) -> dict:
    prov = card.get("provenance") or {}
    res = card["resolution"]
    m = re.match(r"^(.*)-r(\d+)$", source_id)
    caveats = list(sk.caveats) + [str(x) for x in (out.get("caveats") or [])]
    caveats.append("Converted by the converter model from a Claude-drafted v2.6 card: facts, fact ids, which facts each "
                   "consideration rests on, and the reasoning prose are model output; everything else is mechanical. Not authoritative.")
    caveats.append("Option order and ids follow the v2.6 letter order (A->O1...); the verdict's position is therefore as in the source.")
    lib = {
        "domain": spec["domain"], "family": spec["family"], "split_hint": "eval-only",
        "split_hint_why": "Claude-drafted source (B001 / examples-v21); gpt-oss conversion does not make it training-bound until Peter reviews it.",
        "revision_of": case_id_for(m.group(1)) if m else None,
        "source_ids": {o: l for l, o in sk.letter_to_opt.items()},
        "source_consideration_ids": {new: old for old, new in sk.old_to_new.items()},
        "boundary_map": sk.boundary_map,
        "provenance": {
            "source_file": spec["path"], "source_sha256": sha256_file(src_path), "source_id": source_id,
            "source_card_version": card.get("version"), "source_seed": prov.get("seed"),
            "source_drafted_by": prov.get("drafted_by"), "sources": prov.get("sources") or [],
            "converter_role": "converter", "converter_model": model_id, "prompt": PROMPT_VERSION,
            "prompt_sha256": hashlib.sha256(PROMPT_PATH.read_bytes()).hexdigest(),
            "converted_on": today or _dt.date.today().isoformat(), "attempt_that_validated": attempts,
        },
        "review": {"status": "needs_review", "spot_checked_by": None},
        "caveats": caveats,
        "source_caveats": [str(x) for x in (prov.get("caveats") or [])],
        "value_notes": {v["value"]: _collapse(v["here"]) for v in res.get("values", [])},
        "retrieval": card.get("retrieval"),
    }
    if res.get("rests_on"):
        lib["rests_on"] = _collapse(res["rests_on"])
    if m is None:
        lib.pop("revision_of")
    return lib
