"""extract: doc spans -> Scenario, in two model calls per scenario (design v2.2 §7).

  (a) extract_fq.v1: facts (with span ids), question frame, matched option set        [role `extractor`]
  (b) extract_a.v1:  considerations, reasoning, verdict (= the source's endorsed outcome), flip conditions,
                     given F, Q and the spans

Each call is validated (JSON, then the 2a `Case` model which checks every cross-reference, then the gates below);
on failure the errors go back to the model (max 3 attempts per call). Every raw response, accepted or rejected, is
logged under data/store/scenarios/<family>/extract-logs/.

Gate: schema-valid AND every fact has >= 1 span ref or is listed in provenance.authored. Option order is shuffled
by code (seeded by the scenario id) so the real outcome's position is not a cue; option-length cues are flagged.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
from pathlib import Path
from typing import Callable

import yaml
from pydantic import ValidationError

from bench.models import ROOT as MROOT
from bench.models import RefusalError, load_config, role
from bench.schema import Case
from bench.schema.pipeline import Lineage, ProvStep, Provenance, Scenario, SourceRef, sha256_text
from pipeline.store import DATA, Store, _keep_version, write_yaml

from . import option_rules as OR
from . import registry as R
from .normalize import load_spans

PROMPTS = Path(__file__).with_name("prompts")
EQUITY_SET = os.environ.get("BENCHBOOK_EQUITY_SET", "pilot")   # 2026-10-28: corpus batch uses pilot2 (R81)
EQUITIES = DATA.parent / "data" / "registry" / "equities" / f"{EQUITY_SET}.yaml"
MAX_ATTEMPTS = 3
FQ_PROMPT = "extract_fq.v2"          # v1 stays on disk; set to extract_fq.v1 to reproduce older extractions
SPAN_RE = re.compile(r"^src:[0-9a-f]{12}#p\d+\.\d+$")


class TechniqueSkip(Exception):
    """The extractor returned {"skip": "technique", ...}: the decision can't be stated without technique (criterion 4)."""

    def __init__(self, reason: str, step: str):
        super().__init__(f"skip (technique) at {step}: {reason}")
        self.reason, self.step = reason, step


def _skip_check(step: str, validate):
    def v(o):
        if isinstance(o, dict) and o.get("skip"):
            raise TechniqueSkip(str(o.get("reason") or o.get("skip")), step)
        return validate(o)
    return v


class ExtractionError(RuntimeError):
    pass


class IncompleteExtraction(ExtractionError):
    """Extraction could not complete; carries what was extracted so the caller can save it (design 4.3)."""

    def __init__(self, msg, partial=None, missing=(), reason="failed", refusal=None):
        super().__init__(msg)
        self.partial, self.missing, self.reason, self.refusal = partial or {}, list(missing), reason, refusal


# content_domain / refusal_sensitivity defaults when neither the episode nor the source carries them (design 4.2)
DOMAIN_TO_CONTENT = {"personnel security adjudication": "security-clearance", "federal employee gifts and ethics": "gov-ethics"}
CONTENT_SENSITIVITY = {"targeting": "high", "operational-command": "high", "use-of-force-policy": "high", "cyber-policy": "medium",
                       "intel-analysis": "medium", "intel-oversight": "medium", "security-clearance": "low", "gov-ethics": "low"}


def scenario_domain_fields(source: dict, ep: dict) -> dict:
    """content_domain, refusal_sensitivity, held_out: episode > source > mapping from the source domain."""
    cd = ep.get("content_domain") or source.get("content_domain") or DOMAIN_TO_CONTENT.get(source.get("domain", ""))
    if not cd:
        cd = re.sub(r"[^a-z]+", "-", source.get("domain", "unknown").lower()).strip("-")
    rs = ep.get("refusal_sensitivity") or source.get("refusal_sensitivity") or CONTENT_SENSITIVITY.get(cd, "low")
    held = bool(source.get("held_out")) or source.get("domain") in R.HELD_OUT_DOMAINS
    return {"content_domain": cd, "refusal_sensitivity": rs, "held_out": held}


# ------------------------------------------------------------------ helpers
def prompt_file(name: str) -> tuple[str, str, str]:
    p = PROMPTS / f"{name}.md"
    text = p.read_text()
    return text, f"{name}+{hashlib.sha256(text.encode()).hexdigest()[:12]}", hashlib.sha256(text.encode()).hexdigest()


def equities() -> dict[str, str]:
    d = yaml.safe_load(EQUITIES.read_text())
    return {e["id"]: e["gloss"] for e in d["equities"]}


def select_episode_spans(spans: list[dict], ep: dict) -> list[dict]:
    """ep.span_range = [first span id, last span id] (episode finder output), else ep.section (CFR style), else all."""
    rng = ep.get("span_range") or ([ep["span_start"], ep["span_end"]] if ep.get("span_start") else None)
    if rng:
        ids = [s["span"] for s in spans]
        if rng[0] not in ids or rng[1] not in ids or ids.index(rng[0]) > ids.index(rng[1]):
            raise ExtractionError(f"bad span_range {rng}")
        return spans[ids.index(rng[0]):ids.index(rng[1]) + 1]
    return select_spans(spans, ep.get("section"))


def select_spans(spans: list[dict], section: str | None) -> list[dict]:
    if not section:
        return spans
    start = next((i for i, s in enumerate(spans) if s["text"].startswith(f"§ {section}")), None)
    if start is None:
        raise ExtractionError(f"section {section} not found")
    end = next((i for i in range(start + 1, len(spans)) if spans[i]["text"].startswith("§ ")), len(spans))
    return spans[start:end]


def spans_text(spans: list[dict]) -> str:
    return "\n".join(f"[{s['span']}] {s['text']}" for s in spans)


def parse_json(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < 0:
        raise ValueError("no JSON object in reply")
    return json.loads(t[i:j + 1])


def _usage_path() -> Path:
    cfg = load_config()
    return Path(os.environ.get("BENCHBOOK_PROVENANCE") or MROOT / cfg.get("provenance", "results/provenance.jsonl"))


def _read_usage(n_before: int) -> dict:
    p = _usage_path()
    tot = {"calls": 0, "inputTokens": 0, "outputTokens": 0}
    if not p.exists():
        return tot
    for l in p.read_text().splitlines()[n_before:]:
        try:
            r = json.loads(l)
        except ValueError:
            continue
        u = r.get("usage") or {}
        tot["calls"] += 1
        tot["inputTokens"] += u.get("inputTokens", 0)
        tot["outputTokens"] += u.get("outputTokens", 0)
    return tot


def _nlines() -> int:
    p = _usage_path()
    return len(p.read_text().splitlines()) if p.exists() else 0


def call_json(step: str, role_name: str, system: str, user: str, validate: Callable[[dict], list[str]],
              complete_fn: Callable, log_dir: Path, tag: str):
    """-> (obj, attempts, usage). Raises ExtractionError after MAX_ATTEMPTS."""
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    usage = {"calls": 0, "inputTokens": 0, "outputTokens": 0}
    log = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        n0 = _nlines()
        try:
            reply = complete_fn(role_name, msgs, stage=f"extract.{step}")
        except RefusalError as e:       # T2 hook: llm.REFUSAL_HOOK; here a refusal is recorded, never worked around
            log.append({"attempt": attempt, "errors": [f"refusal: {e.reason}"], "reply": e.text})
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / f"{tag}.{step}.log.json").write_text(json.dumps(log, indent=1, ensure_ascii=False))
            raise IncompleteExtraction(f"{tag} {step}: model refused ({e.reason})", reason="refusal",
                                       refusal={"step": step, "reason": e.reason, "model": e.model, "reply_head": e.text[:200]}) from e
        u = _read_usage(n0)
        for k in usage:
            usage[k] += u[k]
        try:
            obj = parse_json(reply)
            errs = validate(obj)
        except (ValueError, json.JSONDecodeError) as e:
            obj, errs = None, [f"reply is not valid JSON: {e}"]
        except (TypeError, AttributeError, KeyError) as e:
            obj, errs = None, [f"malformed structure ({type(e).__name__}: {e}); options must be an object keyed O1.., facts a list of objects"]
        log.append({"attempt": attempt, "errors": errs, "reply": reply})
        log_dir.mkdir(parents=True, exist_ok=True)
        lp = log_dir / f"{tag}.{step}.log.json"
        _keep_version(lp)
        lp.write_text(json.dumps(log, indent=1, ensure_ascii=False))
        if not errs:
            return obj, attempt, usage
        msgs += [{"role": "assistant", "content": reply},
                 {"role": "user", "content": "Your JSON was rejected. Fix ALL of these and return the complete corrected JSON object only:\n- "
                  + "\n- ".join(errs[:25])}]
    raise IncompleteExtraction(f"{tag} {step}: rejected after {MAX_ATTEMPTS} attempts: {errs[:8]}",
                               reason=f"validation failed after {MAX_ATTEMPTS} attempts: {errs[:8]}")


# ------------------------------------------------------------------ F, Q
KINDS = {"situation", "capability", "authority", "intelligence"}
STATUS = {"confirmed", "assessed"}
MOVES = {"act", "partial", "ask", "refuse", "hold"}
ROLES = {"decide", "execute", "advise"}


def fq_texts(o: dict) -> dict[str, str]:
    """Every string in F and Q that must be name- and narration-free."""
    t = {k: str(o.get(k) or "") for k in ("title", "setting", "decider", "agent", "situation", "question")}
    for f in o.get("facts") or []:
        t[f"facts.{f.get('id')}"] = str(f.get("fact") or "")
    for k, v in (o.get("options") or {}).items():
        t[f"options.{k}"] = str(v.get("do") or "")
    return t


def validate_fq(o: dict, allowed_spans: set[str], rules: bool = False, source_text: str = "") -> list[str]:
    """rules=True adds the extract_fq.v2 checks: option justification / form, opposite disposition (R58), names, narration."""
    errs = []
    for k in ("title", "setting", "decider", "agent", "agent_role", "situation", "question", "facts", "options",
              "real_option", "agent_recast"):
        if k not in o:
            errs.append(f"missing key `{k}`")
    if errs:
        return errs
    if o["agent_role"] not in ROLES:
        errs.append(f"agent_role must be one of {sorted(ROLES)}")
    if not 6 <= len(o["facts"]) <= 12:
        errs.append("give 6-10 facts")
    for i, f in enumerate(o["facts"], 1):
        if f.get("id") != f"F{i}":
            errs.append(f"fact {i} must have id F{i}")
        if f.get("kind") not in KINDS:
            errs.append(f"F{i} kind must be one of {sorted(KINDS)}")
        if f.get("status") not in STATUS:
            errs.append(f"F{i} status must be confirmed or assessed")
        if not f.get("fact"):
            errs.append(f"F{i} has no text")
        bad = [s for s in f.get("spans") or [] if s not in allowed_spans]
        if bad and len(bad) < len(f.get("spans") or []):     # repair: keep the valid refs, drop the hallucinated ones
            f["spans"] = [s for s in f["spans"] if s in allowed_spans]
        elif bad:
            errs.append(f"F{i} cites unknown span id {bad[0]}")
    n_auth = sum(1 for f in o["facts"] if not f.get("spans"))
    if n_auth > max(1, len(o["facts"]) // 3):
        errs.append("too many facts without span refs; ground the facts in the document")
    opts = o["options"]
    if not 2 <= len(opts) <= 4:
        errs.append("give 2-4 options")
    for k, v in opts.items():
        if not re.fullmatch(r"O\d+", k):
            errs.append(f"option id {k} must be O<n>")
        if v.get("move") not in MOVES:
            errs.append(f"{k} move must be one of {sorted(MOVES)}")
        if not v.get("do"):
            errs.append(f"{k} has no `do`")
    wc = [len(v.get("do", "").split()) for v in opts.values()]
    if wc and max(wc) > 1.3 * max(1, min(wc)):
        errs.append(f"option lengths {wc} are not matched: rewrite so the longest is at most 1.3x the shortest (in words)")
    if o["real_option"] not in opts:
        errs.append("real_option is not an option id")
    if re.search(r"\{[FCO]\d+\}", o["situation"]):
        errs.append("situation must not contain {id} references")
    if rules:
        errs += OR.option_errors(opts)
        errs += OR.opposite_errors(o)
        texts = fq_texts(o)
        errs += OR.name_errors(texts, source_text)
        errs += OR.narration_errors(texts)
    return errs


def relabel_options(fq: dict, seed: str) -> dict:
    """Shuffle option order (seeded) and relabel O1..On so the real outcome's position is not a cue."""
    ids = list(fq["options"])
    rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest()[:12], 16))
    rng.shuffle(ids)
    new = {f"O{i}": fq["options"][old] for i, old in enumerate(ids, 1)}
    fq = dict(fq)
    fq["options"] = new
    fq["real_option"] = f"O{ids.index(fq['real_option']) + 1}"
    fq["authored_options"] = [k for k in new if k != fq["real_option"]]
    if fq.get("opposite_pair"):
        fq["opposite_pair"] = [f"O{ids.index(p) + 1}" for p in fq["opposite_pair"] if p in ids]
    return fq


def option_cues(fq: dict) -> dict:
    words = {k: len(v["do"].split()) for k, v in fq["options"].items()}
    real = fq["real_option"]
    others = [w for k, w in words.items() if k != real]
    ratio = words[real] / (sum(others) / len(others))
    return {"option_words": words, "real_option": real, "real_to_mean_other_length": round(ratio, 2),
            "real_is_longest": words[real] == max(words.values()),
            "moves": {k: v["move"] for k, v in fq["options"].items()},
            "real_move": fq["options"][real]["move"], "irreversible_flags": {k: v.get("irreversible") for k, v in fq["options"].items()}}


# ------------------------------------------------------------------ A
WEIGHTS = {"strong", "weak", "bar"}


def build_case_dict(sid: str, fq: dict, a: dict, domain: str, family: str, url: str, focus: str, cues: dict) -> dict:
    fc = a.get("flip_conditions") or {}

    def strip(items, drop=("origin", "spans", "repairs")):
        return [{k: v for k, v in i.items() if k not in drop} for i in items or []]

    opts = {}
    for k, v in fq["options"].items():
        o = {"do": v["do"], "move": v["move"]}
        if v.get("irreversible") is not None:
            o["irreversible"] = bool(v["irreversible"])
        if v.get("to"):
            o["to"] = v["to"]
        opts[k] = o
    return {
        "id": sid, "title": fq["title"], "status": "draft", "setting": fq["setting"], "decider": fq["decider"],
        "agent": fq["agent"], "agent_role": fq["agent_role"], "situation": fq["situation"].strip(), "question": fq["question"],
        "options": opts,
        "facts": [{k: f[k] for k in ("id", "kind", "status", "fact")} for f in fq["facts"]],
        "considerations": a.get("considerations"), "reasoning": a.get("reasoning"), "verdict": a.get("verdict"),
        "flip_conditions": {"would_change": strip(fc.get("would_change")), "would_not_change": strip(fc.get("would_not_change")),
                            "watch_for": strip(fc.get("watch_for"))},
        "lesson": a.get("lesson"), "limits": a.get("limits"),
        "library": {"domain": domain, "family": family, "source": url, "episode_focus": focus, "cues": cues},
    }


def validate_a(a: dict, sid: str, fq: dict, eq: dict[str, str], allowed_spans: set[str], mk) -> list[str]:
    errs = []
    for k in ("considerations", "reasoning", "verdict", "flip_conditions", "lesson", "limits", "basis_statement"):
        if k not in a:
            errs.append(f"missing key `{k}`")
    if errs:
        return errs
    real = fq["real_option"]
    if (a["verdict"] or {}).get("choice") != real:
        errs.append(f"verdict.choice must be {real}, the source's real outcome")
    for c in a["considerations"] or []:
        if c.get("equity") not in eq:
            errs.append(f"{c.get('id')}: equity `{c.get('equity')}` is not in the equity list")
        if c.get("weight") not in WEIGHTS:
            errs.append(f"{c.get('id')}: weight must be strong|weak|bar")
    fc = a["flip_conditions"] or {}
    if not fc.get("would_change"):
        errs.append("give at least one would_change flip condition (authored if the source states none)")
    for grp in ("would_change", "would_not_change", "watch_for"):
        for it in fc.get(grp) or []:
            if it.get("origin") not in ("stated", "authored"):
                errs.append(f"{it.get('id')}: origin must be stated|authored")
            bad = [s for s in it.get("spans") or [] if s not in allowed_spans]
            if bad:                     # repair, don't reject: flip conditions are often authored anyway (batch 2026-10-28)
                it["spans"] = [s for s in it["spans"] if s in allowed_spans]
                it.setdefault("repairs", []).append(f"dropped spans outside the episode window: {bad}")
                if it.get("origin") == "stated" and not it["spans"]:
                    it["origin"] = "authored"
                    it["repairs"].append("origin stated -> authored (no span left)")
            if it.get("origin") == "stated" and not it.get("spans"):
                errs.append(f"{it.get('id')}: a `stated` flip condition must cite spans")
    prose = {}
    for k in ("lesson", "limits"):
        prose[k] = str(a.get(k) or "")
    r = a.get("reasoning") or {}
    for k, v in (r.items() if isinstance(r, dict) else []):
        if isinstance(v, str):
            prose[f"reasoning.{k}"] = v
    for c in a.get("considerations") or []:
        prose[f"{c.get('id')}.why"] = str(c.get("why") or "")
    for grp in ("would_change", "would_not_change", "watch_for"):
        for it in fc.get(grp) or []:
            prose[f"{it.get('id')}.if"] = str(it.get("if") or "")
            prose[f"{it.get('id')}.why"] = str(it.get("why") or "")
    errs += OR.narration_errors(prose)           # R40; basis_statement is exempt (it names the source by design)
    try:
        Case.model_validate(mk(a))
    except ValidationError as e:
        errs += [f"schema: {'.'.join(str(x) for x in er['loc'])}: {er['msg']}" for er in e.errors()[:20]]
    except (TypeError, AttributeError, KeyError) as e:
        errs.append(f"schema: malformed structure ({e})")
    return errs


# ------------------------------------------------------------------ one episode
def extract_episode(source: dict, ep: dict, spans: list[dict], sha256: str, split: str, complete_fn: Callable | None = None,
                    data: Path = DATA, addendum: str = "", sid: str | None = None,
                    endorse_fn: Callable[[dict], tuple[str, str]] | None = None) -> Scenario:
    """addendum: extra prompt text appended to both extraction prompts (e.g. prompts/natsec_scope.v1.md); a reply
    {"skip": "technique", ...} then raises TechniqueSkip. sid: explicit scenario id (else derived from family/episodes).
    endorse_fn(fq) -> (option id, why): picks the endorsed option after F/Q (R61: when the authority's finding endorses a
    course other than the one taken); A is then written for that option."""
    if complete_fn is None:
        from bench.models import complete as complete_fn
    family = R.family_of(source, ep)
    n = ep["n"]
    sibs = [e for e in source["episodes"] if R.family_of(source, e) == family]
    k = next((i for i, e in enumerate(sibs, 1) if e is ep), n)       # unique within the document family
    sid = sid or (f"DR-{family}-{k}@v1" if len(sibs) > 1 else f"DR-{family}@v1")
    sel = select_episode_spans(spans, ep)
    allowed = {s["span"] for s in sel}
    log_dir = data / "store" / "scenarios" / family / "extract-logs"
    tag = sid.split("@")[0]
    cfg = role("extractor")
    eq = equities()
    t_fq, v_fq, h_fq = prompt_file(FQ_PROMPT)
    t_a, v_a, h_a = prompt_file("extract_a.v1")
    sys_msg = "You are a careful legal-and-policy analyst building decision scenarios from public documents. Reply with one JSON object only."

    src_text = " ".join(s["text"] for s in sel)
    dom = scenario_domain_fields(source, ep)
    partial = {"id": sid, "family": family, "split": split, "source_id": source.get("id"), "episode": ep.get("focus"), **dom}

    # (a) F, Q
    add = f"\n\n{addendum.strip()}\n" if addendum else ""
    user = t_fq.replace("{{SPANS}}", spans_text(sel)).replace("{{FOCUS}}", ep["focus"]) + add
    fq, att_fq, use_fq = call_json("FQ", "extractor", sys_msg, user,
                                   _skip_check("FQ", lambda o: validate_fq(o, allowed, rules=True, source_text=src_text)),
                                   complete_fn, log_dir, tag)
    fq = relabel_options(fq, sid)
    endorsed = None
    if endorse_fn is not None:
        opt, why = endorse_fn(fq)
        if opt not in fq["options"]:
            raise IncompleteExtraction(f"{sid}: endorsed option {opt!r} is not an option", reason="endorse failed",
                                       missing=["case.verdict"])
        endorsed = {"taken": fq["real_option"], "endorsed": opt, "why": why}
        if opt != fq["real_option"]:
            fq["real_option"] = opt
            fq["authored_options"] = [k for k in fq["options"] if k != opt]
    cues = option_cues(fq)

    # (b) A, given F, Q, spans
    fq_view = {k: fq[k] for k in ("setting", "decider", "agent", "agent_role", "situation", "question", "facts", "options")}
    fq_view["facts"] = [{k: f[k] for k in ("id", "kind", "status", "fact")} for f in fq["facts"]]
    user = (t_a.replace("{{SPANS}}", spans_text(sel)).replace("{{FOCUS}}", ep["focus"])
            .replace("{{FQ}}", json.dumps(fq_view, indent=1, ensure_ascii=False)).replace("{{REAL}}", fq["real_option"])
            .replace("{{EQUITIES}}", "\n".join(f"- {k}: {v}" for k, v in eq.items()))) + add
    mk = lambda a: build_case_dict(sid, fq, a, source["domain"], family, source["url"], ep["focus"], cues)  # noqa: E731
    partial["fq"] = fq
    try:
        a, att_a, use_a = call_json("A", "extractor", sys_msg, user, _skip_check("A", lambda o: validate_a(o, sid, fq, eq, allowed, mk)),
                                    complete_fn, log_dir, tag)
    except IncompleteExtraction as e:
        e.partial = {**partial, "fq_usage": use_fq}
        e.missing = ["case.considerations", "case.reasoning", "case.verdict", "case.flip_conditions", "case.lesson", "case.limits", "basis"]
        raise
    case = Case.model_validate(mk(a))

    # assemble
    fact_spans = {f["id"]: list(f.get("spans") or []) for f in fq["facts"]}
    authored = [f"case.facts.{k}" for k, v in fact_spans.items() if not v]
    authored += [f"case.options.{o}" for o in fq["authored_options"]]
    fc = a["flip_conditions"]
    flip_auth = [it["id"] for g in ("would_change", "would_not_change", "watch_for") for it in fc.get(g) or [] if it["origin"] == "authored"]
    authored += [f"case.flip_conditions.{i}" for i in flip_auth]
    authored += [f"case.{p}" if not p.startswith("case.") else p for p in a.get("authored") or []]
    authored = sorted(set(authored))
    tags = ["options-authored"]
    if OR.no_opposite(fq):
        tags.append("no-opposite")
    elif fq.get("opposite_pair"):
        def _disp(p):
            p = p.get("option") or p.get("id") if isinstance(p, dict) else p
            d = (fq["options"].get(p) or {}).get("disposition", "?") if isinstance(p, str) else "?"
            return d if isinstance(d, str) else str(d.get("word") or d.get("disposition") or "?") if isinstance(d, dict) else str(d)
        tags.append("opposite:" + "|".join(sorted(_disp(p) for p in fq["opposite_pair"])))
    if fq.get("agent_recast"):
        tags.append("agent-recast")
    if flip_auth:
        tags.append("flip-conditions-authored")
    if cues["real_is_longest"] or not 0.8 <= cues["real_to_mean_other_length"] <= 1.25:
        tags.append("cue:option-length")
    if endorsed:
        tags.append("gold-endorsed-alternative" if endorsed["taken"] != endorsed["endorsed"] else "gold-endorsed-taken")
    if cues["real_move"] in ("ask", "hold", "refuse"):
        tags.append(f"gold-move:{cues['real_move']}")
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    prm = {"temperature": cfg.get("temperature"), "max_tokens": cfg.get("max_tokens"), "reasoning_effort": cfg.get("reasoning_effort")}
    prov = Provenance(steps=[
        ProvStep(id="extract.FQ", operator="extract", model=cfg.model, role="extractor", prompt_version=v_fq,
                 inputs={"doc": sha256, "prompt": h_fq, "spans": sha256_text(spans_text(sel))},
                 params={**prm, "attempts": att_fq, "usage": use_fq}, ts=ts,
                 notes=(fq.get("recast_note") or None)),
        ProvStep(id="extract.A", operator="extract", model=cfg.model, role="extractor", prompt_version=v_a,
                 inputs={"doc": sha256, "prompt": h_a, "fq": sha256_text(json.dumps(fq_view, sort_keys=True))},
                 params={**prm, "attempts": att_a, "usage": use_a}, ts=ts,
                 notes=("; ".join(a.get("equity_gaps") or []) or None)),
        *([ProvStep(id="extract.endorse", operator="extract", model=cfg.model, role="extractor", ts=ts,
                    notes=f"option taken by the decider (per source): {endorsed['taken']}; option the authority's finding "
                          f"endorses (verdict): {endorsed['endorsed']}; {endorsed['why']}")] if endorsed else []),
        ProvStep(id="extract.assign", operator="extract", notes=f"family {family}; split {split} by rule: {R.SPLIT_RULE}; "
                 "option order shuffled by code (seed = scenario id)", ts=ts),
    ], fields={**{f"case.{k}": "extract.FQ" for k in ("title", "setting", "decider", "agent", "agent_role", "situation", "question",
                                                       "options", "facts")},
               **{f"case.{k}": "extract.A" for k in ("considerations", "reasoning", "verdict", "flip_conditions", "lesson", "limits")},
               "family": "extract.assign", "split": "extract.assign"},
        authored=authored)
    s = Scenario(id=sid, family=family, split=split, domain=source["domain"], status="needs_review", case=case, **dom,
                 verdict_tier="source-endorsed", basis=a["basis_statement"],
                 source=SourceRef(sha256=sha256, doc=f"data/docs/{sha256[:12]}.jsonl", url=source["url"], title=source["title"],
                                  kind=source["kind"], license=source["license"]),
                 fact_spans=fact_spans, tags=tags, lineage=Lineage(operator="extract", detail={"episode": ep["focus"]}),
                 provenance=prov)
    try:
        gate(s)
    except ExtractionError as e:
        raise IncompleteExtraction(str(e), partial={**partial, "scenario": s.dump()}, reason="gate failed (fewer than 4 grounded facts or ungrounded fact)",
                                   missing=["case.facts"]) from e
    return s


def gate(s: Scenario):
    """Schema-valid (constructing Scenario already checked) AND every fact grounded or listed as authored."""
    errs = []
    for f in s.case.facts:
        if not s.fact_spans.get(f.id) and f"case.facts.{f.id}" not in s.provenance.authored:
            errs.append(f"{f.id} has no span ref and is not listed as authored")
    if len(s.grounded_facts()) < 4:
        errs.append("fewer than 4 grounded facts")
    if errs:
        raise ExtractionError(f"{s.id}: gate failed: {errs}")


def save_incomplete(e: IncompleteExtraction, family: str, sid: str, data: Path = DATA) -> Path:
    """data/store/incomplete/<family>/<id>.yaml: everything extracted + `missing:` + reason. Never paired or trained on."""
    p = data / "store" / "incomplete" / family / (sid.replace("@", "-") + ".yaml")
    rec = {"id": sid, "family": family, "reason": e.reason, "message": str(e)[:600], "missing": e.missing or ["case"],
           "refusal": e.refusal, "extracted": e.partial, "status": "incomplete",
           "note": "never paired, rendered or trained on until completed and passing the gates (design 4.3)"}
    write_yaml(p, rec)
    return p


def extract_all(source_id: str | None = None, episode: int | None = None, complete_fn=None, data: Path = DATA) -> list[str]:
    reg = R.load_registry()
    acq = R.load_acquired()
    st = Store(data)
    out = []
    for src in reg["sources"]:
        if source_id and src["id"] != source_id:
            continue
        sha = acq[src["id"]]["sha256"]
        spans = load_spans(sha[:12])
        for ep in src["episodes"]:
            if episode and ep["n"] != episode:
                continue
            family = R.family_of(src, ep)
            sibs = [e for e in src["episodes"] if R.family_of(src, e) == family]
            k = next((i for i, e in enumerate(sibs, 1) if e is ep), ep["n"])
            sid = f"DR-{family}-{k}@v1" if len(sibs) > 1 else f"DR-{family}@v1"
            try:
                s = extract_episode(src, ep, spans, sha, reg["splits"][family], complete_fn, data=data)
            except IncompleteExtraction as e:
                if not e.partial:
                    e.partial = {"id": sid, "family": family, "source_id": src["id"], "episode": ep.get("focus"), **scenario_domain_fields(src, ep)}
                    e.missing = e.missing or ["case.facts", "case.options", "case.situation", "case.question"]
                p = save_incomplete(e, family, sid, data)
                out.append(f"INCOMPLETE {src['id']} ep{ep['n']}: {e.reason[:120]} -> {p}")
                continue
            except ExtractionError as e:
                out.append(f"REJECTED {src['id']} ep{ep['n']}: {e}")
                continue
            st.save_scenario(s)
            out.append(f"{s.id} split={s.split} facts={len(s.grounded_facts())}/{len(s.case.facts)} choice={s.case.verdict.choice} tags={s.tags}")
    return out
