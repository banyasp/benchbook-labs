from __future__ import annotations

import copy
import hashlib
import json
import random
import re
import time
from pathlib import Path

import yaml

from bench.schema import Case
from bench.schema.pipeline import Lineage, Scenario, sha256_text
from pipeline.store import Store, write_yaml

PROMPTS = Path(__file__).resolve().parent / "prompts"
ROOT = Path(__file__).resolve().parents[3]


def complete(role: str, messages: list[dict]) -> str:
    from bench.models import complete as c
    return c(role, messages, stage=role)


def extract_json(text: str):
    from pipeline.render.util import extract_json as ej
    return ej(text)


# ------------------------------------------------------------------ sketch parsing
SEC = re.compile(r"^## (\d+)\. (.+?)\n(.*?)(?=^## \d+\. |\Z)", re.S | re.M)
SIS = re.compile(r"^\*\*Sister ([AB]): (.+?)\*\* \((.+?)\)\s*\n(.*?)(?=^\*\*Sister [AB]:|^---|\Z)", re.S | re.M)
SID = re.compile(r"`(DR-[^`]+@v\d+)`")


def parse_sketch(path: str) -> list[dict]:
    text = Path(path).read_text()
    out = []
    for m in SEC.finditer(text):
        num, title, body = m.group(1), m.group(2).strip(), m.group(3)
        sid = SID.search(body)
        if not sid:
            continue
        head = body.split("**Sister")[0]
        for s in SIS.finditer(body):
            out.append({"anchor": sid.group(1), "anchor_no": int(num), "anchor_title": title, "anchor_sketch": head.strip(),
                        "sister": s.group(1), "title": s.group(2).strip(), "subdomain": s.group(3).strip(),
                        "sketch": s.group(4).strip(), "flagged": "FLAG" in s.group(4), "sketch_file": str(path)})
    return out


# ------------------------------------------------------------------ helpers
def anchor_case(T: Scenario) -> dict:
    c = T.case.model_dump(mode="json", by_alias=True, exclude_none=True)
    c.pop("library", None)
    return c


def sister_id(anchor_id: str, sister: str, suffix: str = "") -> str:
    stem = anchor_id.removeprefix("DR-").split("@")[0]
    return f"DR-XFER-{stem}-{sister}{suffix}@v1"


def permute_options(case: dict, rng: random.Random) -> dict:
    """Shuffle option ids so the card's option order does not mirror the anchor's (position cue)."""
    old = list(case["options"])
    new = old[:]
    rng.shuffle(new)
    m = dict(zip(old, new))
    if all(a == b for a, b in m.items()):
        return case
    c = copy.deepcopy(case)
    c["options"] = {m[k]: v for k, v in case["options"].items()}
    c["options"] = dict(sorted(c["options"].items(), key=lambda kv: int(re.sub(r"\D", "", kv[0]) or 0)))
    for k in c.get("considerations", []):
        k["favors"] = [m.get(o, o) for o in k.get("favors", [])]
    v = c.get("verdict", {})
    if v.get("choice") in m:
        v["choice"] = m[v["choice"]]
    r = c.get("reasoning", {}) or {}
    tw = r.get("tempting_wrong") or {}
    if isinstance(tw, dict) and tw.get("option") in m:
        tw["option"] = m[tw["option"]]
    if isinstance(r.get("rejected"), dict):
        r["rejected"] = {m.get(k, k): v for k, v in r["rejected"].items()}
    for w in (c.get("flip_conditions", {}) or {}).get("would_change", []) or []:
        if w.get("then") in m:
            w["then"] = m[w["then"]]
    c.setdefault("_option_permutation", m)
    return c


def structure_errors(new: dict, ref: dict, *, same_k: bool = True, verdict: str | None = None) -> list[str]:
    errs = []
    try:
        Case.model_validate({k: v for k, v in new.items() if not k.startswith("_")})
    except Exception as e:                                           # noqa: BLE001
        errs.append(f"schema: {str(e)[:600]}")
    if set(new.get("options", {})) != set(ref["options"]):
        errs.append(f"option ids {sorted(new.get('options', {}))} must be {sorted(ref['options'])}")
    fids = {f.get("id") for f in new.get("facts", [])}
    for k in new.get("considerations", []):
        bad = [f for f in k.get("facts", []) if f not in fids]
        if bad:
            errs.append(f"consideration {k.get('id')} cites unknown facts {bad}")
    if same_k:
        a = {k["id"]: (k["equity"], sorted(k["favors"]), k["weight"]) for k in ref["considerations"]}
        b = {k.get("id"): (k.get("equity"), sorted(k.get("favors", [])), k.get("weight")) for k in new.get("considerations", [])}
        if a != b:
            errs.append(f"considerations must keep ids, equities, favors and weights exactly: want {a}, got {b}")
        if new.get("verdict", {}).get("choice") != ref["verdict"]["choice"]:
            errs.append(f"verdict.choice must be {ref['verdict']['choice']}")
    if verdict and new.get("verdict", {}).get("choice") != verdict:
        errs.append(f"verdict.choice must be {verdict}")
    if len(new.get("facts", [])) < 4:
        errs.append("too few facts")
    return errs


def llm_json(role: str, system: str, user: str, check, tries: int = 3) -> tuple[dict | None, list[dict]]:
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    log = []
    for i in range(tries):
        raw = complete(role, msgs)
        try:
            obj = extract_json(raw)
        except Exception as e:                                       # noqa: BLE001
            log.append({"try": i, "error": f"unparseable: {e}"[:200]})
            msgs += [{"role": "assistant", "content": raw[:8000]},
                     {"role": "user", "content": "That was not valid JSON. Return the full JSON object only."}]
            continue
        errs = check(obj)
        log.append({"try": i, "errors": errs[:5]})
        if not errs:
            return obj, log
        msgs += [{"role": "assistant", "content": raw[:12000]},
                 {"role": "user", "content": "Fix these problems and return the full JSON object only:\n- " + "\n- ".join(errs[:10])}]
    return None, log


# ------------------------------------------------------------------ write X2 and X2'
def write_sister(T1: Scenario, sk: dict) -> tuple[dict | None, list]:
    ref = anchor_case(T1)
    system = (PROMPTS / "write.v1.md").read_text()
    user = ("ANCHOR CASE (JSON):\n" + json.dumps(ref, ensure_ascii=False, indent=1)
            + f"\n\nSKETCH OF THE SISTER (sub-domain: {sk['subdomain']}; title: {sk['title']}):\n{sk['sketch']}"
            + f"\n\nANCHOR SUMMARY FROM THE SKETCH FILE:\n{sk['anchor_sketch'][:3000]}")
    return llm_json("transfer_writer", system, user, lambda o: structure_errors(o, ref))


def write_flip(x2: dict, item: dict) -> tuple[dict | None, list]:
    system = (PROMPTS / "flip.v1.md").read_text()
    clean = {k: v for k, v in x2.items() if not k.startswith("_")}
    user = ("CASE (JSON):\n" + json.dumps(clean, ensure_ascii=False, indent=1)
            + "\n\nFLIP CONDITION TO MAKE TRUE:\n" + json.dumps(item, ensure_ascii=False))
    return llm_json("transfer_writer", system, user,
                    lambda o: structure_errors(o, clean, same_k=False, verdict=item["then"]))


# ------------------------------------------------------------------ checks
def equities_block() -> str:
    eq = yaml.safe_load((ROOT / "data/registry/equities/pilot2.yaml").read_text())["equities"]
    return "\n".join(f"- {e['id']}: {e['gloss']}" for e in eq)


def blind_solve(case: dict) -> dict:
    system = (PROMPTS / "solve.v1.md").read_text()
    shown = {k: case[k] for k in ("setting", "decider", "agent", "agent_role", "situation", "question", "facts") if k in case}
    shown["options"] = {k: v["do"] for k, v in case["options"].items()}
    user = "EQUITIES:\n" + equities_block() + "\n\nSCENARIO (JSON):\n" + json.dumps(shown, ensure_ascii=False, indent=1)
    obj, _ = llm_json("transfer_checker", system, user, lambda o: [] if o.get("choice") else ["missing choice"], tries=2)
    return obj or {}


def adds_probe(case: dict) -> dict:
    system = (PROMPTS / "adds.v2.md").read_text()   # v1 over-reported, also on real anchors
    shown = {k: case[k] for k in ("setting", "decider", "agent", "situation", "question", "facts") if k in case}
    shown["options"] = {k: v["do"] for k, v in case["options"].items()}
    shown["considerations"] = [{x: k.get(x) for x in ("equity", "favors", "weight", "why")} for k in case["considerations"]]
    user = "EQUITIES:\n" + equities_block() + "\n\nSCENARIO WITH ITS CONSIDERATIONS (JSON):\n" + json.dumps(shown, ensure_ascii=False, indent=1)
    obj, _ = llm_json("transfer_checker", system, user, lambda o: [] if "missing" in o else ["missing key 'missing'"], tries=2)
    return obj or {"missing": [], "error": "probe failed"}


def k_agreement(case: dict, solved: dict) -> dict:
    gold = [(k["equity"], set(k["favors"])) for k in case["considerations"]]
    got = [(k.get("equity"), set(k.get("favors") or [])) for k in solved.get("considerations") or []]
    eq_hit = sum(1 for e, _ in gold if any(e == g for g, _ in got))
    dir_hit = sum(1 for e, f in gold if any(e == g and (f & h) for g, h in got))
    return {"n": len(gold), "equity_found": eq_hit, "equity_and_direction": dir_hit,
            "choice": solved.get("choice"), "agrees": solved.get("choice") == case["verdict"]["choice"]}


_ANCHOR_BASE: dict = {}


def anchor_baseline(T1: Scenario) -> dict:
    """Blind solve and probe on the anchor itself: the reference the sister checks are compared with."""
    if T1.id not in _ANCHOR_BASE:
        a = anchor_case(T1)
        solved = blind_solve(a)
        probe = adds_probe(a)
        _ANCHOR_BASE[T1.id] = {"blind_choice": solved.get("choice"), "blind": k_agreement(a, solved),
                               "adds_strong": [m for m in probe.get("missing", [])
                                               if str(m.get("weight", "")).lower() in ("strong", "bar")]}
    return _ANCHOR_BASE[T1.id]


def run_checks(case_dict: dict, sid: str) -> dict:
    from pipeline.ingest import technique_check as TC
    from pipeline.render import answer_leak as AL
    out = {}
    tmp = to_scenario(case_dict, sid, family="XFER-tmp", parent="tmp", operator="check", detail={})
    try:
        lk = AL.check(tmp, None)
        out["leak"] = {"frame": lk.get("frame") or [], "facts": lk.get("facts") or []}
    except Exception as e:                                            # noqa: BLE001
        out["leak"] = {"error": str(e)[:200]}
    txt = json.dumps({k: v for k, v in case_dict.items() if not k.startswith("_")}, ensure_ascii=False)
    out["technique"] = [f.match for f in TC.check(txt) if f.severity == "strip"]
    solved = blind_solve(case_dict)
    out["blind"] = k_agreement(case_dict, solved)
    out["blind_raw"] = solved
    out["adds"] = adds_probe(case_dict)
    out["adds_strong"] = [m for m in out["adds"].get("missing", []) if str(m.get("weight", "")).lower() in ("strong", "bar")]
    return out


def to_scenario(case_dict: dict, sid: str, *, family: str, parent: str, operator: str, detail: dict,
                domain: str = "transfer", anchor: Scenario | None = None) -> Scenario:
    c = {k: v for k, v in case_dict.items() if not k.startswith("_")}
    c["id"] = sid
    if anchor is not None:
        lib = copy.deepcopy(anchor.case.library) if anchor.case.library else {}
        if isinstance(lib, dict):
            lib.update({"domain": domain, "family": family, "source": f"transfer of {anchor.id}"})
            lib.pop("cues", None)
        c["library"] = lib
    return Scenario.model_validate({
        "id": sid, "family": family, "split": "eval-only", "domain": domain, "status": "derived",
        "case": c, "verdict_tier": "by-construction",
        "basis": (f"transferred from {parent}: considerations, reasoning and verdict carried over from the anchor"
                  if operator == "transfer" else f"{operator} of {parent}: the stated flip condition made true"),
        "tags": ["transfer", "synthetic", operator], "lineage": Lineage(parent=parent, operator=operator, detail=detail).model_dump()})


def save(store: Store, S: Scenario, bucket: str) -> Path:
    if bucket == "accepted":
        return store.save_scenario(S)
    d = store.root / ("transfer-hard" if bucket == "hard" else "transfer-rejected")
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{S.id}.yaml"
    write_yaml(p, S.dump())
    return p


def bucket_of(chk: dict) -> tuple[str, str]:
    if chk.get("technique"):
        return "rejected", "technique"
    lk = chk.get("leak", {})
    if lk.get("error") or lk.get("frame") or lk.get("facts"):
        return "rejected", "answer leak"
    if chk.get("adds_new_vs_anchor", chk.get("adds_strong")):
        return "hard", "the setting adds a strong consideration the anchor does not have"
    return "accepted", "ok"


def build_one(store: Store, sk: dict, seed: int = 0) -> dict:
    T1 = store.scenario(sk["anchor"])
    sid = sister_id(T1.id, sk["sister"])
    rec = {"sister": sid, "anchor": T1.id, "title": sk["title"], "subdomain": sk["subdomain"], "sketch_flag": sk["flagged"],
           "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    x2, log = write_sister(T1, sk)
    rec["write_log"] = log
    if x2 is None:
        rec["final"] = "write failed"
        return rec
    rng = random.Random(int(hashlib.sha256(sid.encode()).hexdigest()[:8], 16) + seed)
    x2 = permute_options(x2, rng)
    fam = f"XFER-{T1.family}"
    detail = {"subdomain": sk["subdomain"], "sister": sk["sister"], "title": sk["title"], "sketch_file": sk["sketch_file"],
              "sketch_flag": sk["flagged"], "option_permutation": x2.get("_option_permutation", {})}
    chk = run_checks(x2, sid)
    base = anchor_baseline(T1)
    inv = {v: k for k, v in (x2.get("_option_permutation") or {}).items()}
    bc = chk["blind"].get("choice")
    chk["equivalence"] = {"anchor_blind_choice": base["blind_choice"], "sister_blind_choice_as_anchor_id": inv.get(bc, bc),
                          "same": inv.get(bc, bc) == base["blind_choice"], "anchor_blind_agrees_with_source": base["blind"]["agrees"]}
    anchor_eq = {m.get("equity") for m in base["adds_strong"]}
    chk["adds_new_vs_anchor"] = _against(chk["adds_strong"], anchor_eq, x2["verdict"]["choice"])
    b, why = bucket_of(chk)
    S2 = to_scenario(x2, sid, family=fam, parent=T1.id, operator="transfer", detail={**detail, "checks": _slim(chk)},
                     domain=sk["subdomain"], anchor=T1)
    rec.update(bucket=b, why=why, path=str(save(store, S2, b)), checks=_slim(chk))
    # flip variant from the first would_change item
    wc = (x2.get("flip_conditions") or {}).get("would_change") or []
    if wc and b != "rejected":
        item = wc[0]
        x2f, flog = write_flip({k: v for k, v in x2.items() if k != "_option_permutation"}, item)
        rec["flip_log"] = flog
        if x2f is not None:
            fid = sister_id(T1.id, sk["sister"], "-flip1")
            fchk = run_checks(x2f, fid)
            fchk["adds_new_vs_anchor"] = _against(fchk["adds_strong"], anchor_eq, item.get("then"))
            fbc = fchk["blind"].get("choice")
            fchk["equivalence"] = {"blind_choice_as_anchor_id": inv.get(fbc, fbc), "then_as_anchor_id": inv.get(item.get("then"), item.get("then")),
                                   "blind_reaches_then": fbc == item.get("then")}
            fb, fwhy = bucket_of(fchk)
            if fb == "accepted" and b == "hard":
                fb = "hard"
            S3 = to_scenario(x2f, fid, family=fam, parent=sid, operator="transfer-flip",
                             detail={**detail, "flip_item": item, "checks": _slim(fchk)}, domain=sk["subdomain"], anchor=T1)
            rec["flip"] = {"id": fid, "bucket": fb, "why": fwhy, "path": str(save(store, S3, fb)), "checks": _slim(fchk),
                           "then": item.get("then")}
    rec["final"] = "done"
    return rec


def _against(adds: list, anchor_eq: set, verdict: str) -> list:
    """Strong additions that could change the decision: not also found on the anchor, and either a bar or pulling
    toward an option other than the verdict (an addition that only reinforces the verdict changes nothing)."""
    out = []
    for m in adds:
        if m.get("equity") in anchor_eq:
            continue
        if str(m.get("weight", "")).lower() == "bar" or any(o != verdict for o in (m.get("favors") or [])):
            out.append(m)
    return out


def _slim(chk: dict) -> dict:
    return {"leak": chk.get("leak"), "technique": chk.get("technique"), "blind": chk.get("blind"),
            "equivalence": chk.get("equivalence"), "adds_strong": chk.get("adds_strong"),
            "adds_new_vs_anchor": chk.get("adds_new_vs_anchor"), "adds_all": (chk.get("adds") or {}).get("missing")}
