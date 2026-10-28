"""Shared machinery for the perturb operators.

Structural facts (ids, options, verdict, gold maps) are built in Python; models only write language. A model
reply is always JSON, validated by a callback; a rejection is fed back to the model (up to `tries` attempts).
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from bench.schema import Case
from bench.schema.common import PROSE_REF
from bench.schema.pipeline import (FrameCmp, GoldMap, GPair, Lineage, ProvStep, Provenance, Scenario, sha256_obj,
                                   sha256_text)

PROMPTS = Path(__file__).resolve().parent / "prompts"
SHORT = {"restyle": "restyle", "flip": "flip", "add_fact": "addfact", "revise_card": "revise"}
KINDS = ("situation", "capability", "authority", "intelligence")
STATUSES = ("confirmed", "assessed")


class OperatorError(RuntimeError):
    pass


class RefusalError(OperatorError):
    """The model refused (refusal-shaped reply). Not retried; `.step` is the recorded provenance step (refusal: true)."""

    def __init__(self, msg, step=None):
        super().__init__(msg)
        self.step = step


REFUSAL = re.compile(r"I can'?t help|I cannot assist|I can'?t assist|I'm sorry, but|I am sorry, but|I cannot help", re.I)


def is_refusal(text) -> bool:
    """Simple detection until W4's datagen/llm.py refusal recording exists: empty output, or refusal wording."""
    if text is None or not str(text).strip():
        return True
    t = str(text).strip()
    return bool(REFUSAL.match(t)) or (len(t) < 400 and "{" not in t and bool(REFUSAL.search(t)))


# ------------------------------------------------------------------ model access (injectable for tests)
_COMPLETE = None


def set_complete(fn):
    """Install a stand-in for bench.models.complete (tests). fn(role, messages, **kw) -> str. None restores."""
    global _COMPLETE
    _COMPLETE = fn


def complete(role: str, messages: list[dict], **kw) -> str:
    if _COMPLETE is not None:
        return _COMPLETE(role, messages, **kw)
    from bench.models import complete as real
    return real(role, messages, **kw)


def model_of(role: str) -> str:
    try:
        from bench.models import role as get_role
        return get_role(role).model
    except Exception:
        return "unknown"


def prompt(name: str) -> tuple[str, str]:
    """(text, 'name.v1+sha12') of prompts/<name>.md."""
    t = (PROMPTS / f"{name}.md").read_text()
    return t, f"{name}+{sha256_text(t)[:12]}"


def _transcript(op, name, role, attempt, msgs, text):
    """PERTURB_TRANSCRIPT=<file.jsonl>: append every model exchange (debugging / live-check record)."""
    import os
    path = os.environ.get("PERTURB_TRANSCRIPT")
    if path:
        with open(path, "a") as f:
            f.write(json.dumps({"op": op, "stage": name, "role": role, "attempt": attempt, "messages": msgs, "reply": text},
                               ensure_ascii=False) + "\n")


def parse_json(text: str):
    t = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < i:
        raise ValueError("no JSON object found in the reply")
    try:
        return json.loads(t[i:j + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"reply is not valid JSON: {e}")


@dataclass
class Ctx:
    """One operator run: the parent, the store, an rng, and the provenance being accumulated."""
    op: str
    X: Scenario
    store: object
    rng: random.Random
    prov: Provenance = field(default_factory=Provenance)
    calls: int = 0

    def ask(self, role: str, name: str, system: str, user: str, validate=None, tries: int = 3, step_id: str | None = None):
        sys_text, pv = prompt(system)
        msgs = [{"role": "system", "content": sys_text}, {"role": "user", "content": user}]
        last = None
        for attempt in range(tries):
            self.calls += 1
            try:
                text = complete(role, msgs, stage=f"perturb.{self.op}.{name}")
            except Exception as e:                      # a refusal exposed by the model layer (W4): attribute `refusal`
                if getattr(e, "refusal", False):
                    self._refused(role, pv, user, attempt, str(e))
                raise
            _transcript(self.op, name, role, attempt, msgs, text)
            if is_refusal(text):
                self._refused(role, pv, user, attempt, (text or "")[:200], step_id or f"{self.op}.{name}")
            try:
                obj = parse_json(text)
                res = validate(obj) if validate else obj
                self.prov.step(id=step_id or f"{self.op}.{name}", operator="perturb", model=model_of(role), role=role,
                               prompt_version=pv, inputs={"parent": sha256_obj(self.X.dump()), "user": sha256_text(user)},
                               params={"attempts": attempt + 1}, ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
                return res, text
            except ValueError as e:
                last = e
                msgs += [{"role": "assistant", "content": text},
                         {"role": "user", "content": f"Rejected: {e}\nFix this and resend the complete JSON object."}]
        raise OperatorError(f"{self.op}.{name}: no valid reply after {tries} attempts: {last}")

    def _refused(self, role, pv, user, attempt, detail, step_id=None):
        step = self.prov.step(id=(step_id or f"{self.op}.refused") + ".refused", operator="perturb", model=model_of(role), role=role,
                              prompt_version=pv, inputs={"parent": sha256_obj(self.X.dump()), "user": sha256_text(user)},
                              params={"attempts": attempt + 1, "refusal": True}, notes=f"refusal: {detail}"[:300],
                              ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        raise RefusalError(f"{self.op}: model refused ({detail[:120]!r})", step)

    def code_step(self, id: str, notes: str, params: dict | None = None):
        self.prov.step(id=id, operator="perturb", notes=notes, params=params or {},
                       inputs={"parent": sha256_obj(self.X.dump())}, ts=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


def seed_rng(*parts) -> random.Random:
    return random.Random(int(sha256_text("|".join(map(str, parts)))[:12], 16))


# ------------------------------------------------------------------ ids
def next_id(store, family: str, op: str) -> str:
    stem = f"DR-{family}-{SHORT[op]}"
    used = set()
    for p in (store.root / "scenarios").glob(f"*/{stem}*@v1.yaml"):
        m = re.fullmatch(re.escape(stem) + r"(\d+)@v1", p.stem)
        if m:
            used.add(int(m.group(1)))
    return f"{stem}{max(used, default=0) + 1}@v1"


# ------------------------------------------------------------------ skeleton (T numbering)
@dataclass
class Edit:
    action: str                 # replace | add | remove
    fact: str | None = None     # C fact id (replace / remove)
    text: str | None = None
    kind: str | None = None
    status: str | None = None


@dataclass
class Skeleton:
    d: dict                                          # T case dict, T numbering; texts = C's except edited facts
    c2t: dict[str, str | None]                       # C fact id -> T fact id (None = removed)
    origin: dict[str, str]                           # T fact id -> matched | corresponding | new
    t2c: dict[str, str]                              # T fact id -> C fact id (matched / corresponding)
    fixed: set[str]                                  # T fact ids whose text is fixed by the operator
    spans: dict[str, list[str]]                      # T fact id -> span ids (carried for matched)


def build_skeleton(X: Scenario, edits: list[Edit], rng: random.Random, remap_prose: bool = True) -> Skeleton:
    C = X.case
    d = copy.deepcopy(C.dump())
    by_fact = {e.fact: e for e in edits if e.action in ("replace", "remove")}
    entries = []                                     # (origin, c id, kind, status, text, fixed)
    for f in C.facts:
        e = by_fact.get(f.id)
        if e and e.action == "remove":
            continue
        if e and e.action == "replace":
            entries.append(["corresponding", f.id, e.kind or f.kind, e.status or f.status, e.text, True])
        else:
            entries.append(["matched", f.id, f.kind, f.status, f.fact, False])
    for e in [e for e in edits if e.action == "add"]:
        entries.insert(rng.randint(0, len(entries)), ["new", None, e.kind or "situation", e.status or "confirmed", e.text, True])
    c2t = {f.id: None for f in C.facts}
    origin, t2c, fixed, spans, facts = {}, {}, set(), {}, []
    for n, (org, cid, kind, status, text, fx) in enumerate(entries, 1):
        tid = f"F{n}"
        facts.append({"id": tid, "kind": kind, "status": status, "fact": text})
        origin[tid] = org
        if cid:
            c2t[cid] = tid
            t2c[tid] = cid
            if org == "matched":
                spans[tid] = list(X.fact_spans.get(cid, []))
        if fx:
            fixed.add(tid)
    d["facts"] = facts
    for c in d["considerations"]:
        c["facts"] = [c2t[f] for f in c["facts"] if c2t.get(f)]

    def fix(s):
        if not isinstance(s, str) or not remap_prose:
            return s
        return PROSE_REF.sub(lambda m: ("{" + c2t[m.group(1)] + "}") if m.group(1) in c2t and c2t[m.group(1)]
                             else ("[removed fact]" if m.group(1) in c2t else m.group(0)), s)

    def walk(o):
        if isinstance(o, dict):
            return {k: walk(v) for k, v in o.items()}
        if isinstance(o, list):
            return [walk(v) for v in o]
        return fix(o)
    for key in ("situation", "lesson", "limits"):
        d[key] = fix(d[key])
    for key in ("reasoning", "considerations", "flip_conditions"):
        d[key] = walk(d[key])
    return Skeleton(d, c2t, origin, t2c, fixed, spans)


# ------------------------------------------------------------------ text bundles
SCALARS_FQ = ("setting", "decider", "agent", "situation", "question")
REASON = ("read", "weighing", "tradecraft", "uncertainty", "handoff")


def bundle(d: dict, sections: set[str], fixed: set[str] = frozenset()) -> dict:
    b = {}
    if "fq" in sections:
        b.update({k: d[k] for k in SCALARS_FQ})
        b["options"] = {k: v["do"] for k, v in d["options"].items()}
        b["facts"] = {f["id"]: ({"text": f["fact"], "fixed": True} if f["id"] in fixed else f["fact"]) for f in d["facts"]}
    if "a" in sections:
        b["considerations"] = {c["id"]: {"facts": c["facts"], "equity": c["equity"], "favors": c["favors"],
                                         "weight": c["weight"], **({"rules_out": c["rules_out"]} if c.get("rules_out") else {}),
                                         "why": c["why"]} for c in d["considerations"]}
        b["verdict"] = {"choice": d["verdict"]["choice"], "decisive": d["verdict"]["decisive"]}
        r = d["reasoning"]
        b["reasoning"] = {**{k: r[k] for k in REASON}, "tempting_wrong": dict(r["tempting_wrong"]), "rejected": dict(r["rejected"])}
        fc = d["flip_conditions"]
        b["flip"] = {**{w["id"]: {"if": w["if"], "then": w["then"], "why": w["why"]} for w in fc["would_change"]},
                     **{w["id"]: {"if": w["if"], "why": w["why"]} for w in fc.get("would_not_change", [])},
                     **{w["id"]: {"what": w["what"], "favors": w["favors"], "why": w["why"]} for w in fc.get("watch_for", [])}}
        b["lesson"], b["limits"] = d["lesson"], d["limits"]
    return b


_TIDY = str.maketrans({"\u2011": "-", "\u2010": "-", "\u2012": "-", "\u00a0": " ", "\u202f": " ", "\u2019": "'", "\u2018": "'",
                       "\u201c": '"', "\u201d": '"'})


def _s(o, where):
    if not isinstance(o, str) or not o.strip():
        raise ValueError(f"{where} must be a non-empty string")
    return o.translate(_TIDY).strip()


def apply_text(d: dict, out: dict, sections: set[str], fixed: set[str] = frozenset(), free_reasoning: bool = False):
    """Write model-authored text from `out` into case dict `d` (in place). Raises ValueError on a missing key."""
    if "fq" in sections:
        for k in SCALARS_FQ:
            d[k] = _s(out.get(k), k)
        ot = out.get("options") or {}
        for oid, o in d["options"].items():
            o["do"] = _s(ot.get(oid), f"options.{oid}")
        ft = out.get("facts") or {}
        for f in d["facts"]:
            if f["id"] in fixed:
                continue
            v = ft.get(f["id"])
            f["fact"] = _s(v.get("text") if isinstance(v, dict) else v, f"facts.{f['id']}")
    if "a" in sections:
        ct = out.get("considerations") or {}
        for c in d["considerations"]:
            v = ct.get(c["id"])
            if isinstance(v, dict):
                v = v.get("why")
            if v is None and (ct.get(c["id"]) or {}).get("drop"):
                continue
            c["why"] = _s(v, f"considerations.{c['id']}.why")
        r, ro = d["reasoning"], out.get("reasoning") or {}
        for k in REASON:
            r[k] = _s(ro.get(k), f"reasoning.{k}")
        tw = ro.get("tempting_wrong") or {}
        r["tempting_wrong"]["pull"] = _s(tw.get("pull"), "reasoning.tempting_wrong.pull")
        r["tempting_wrong"]["why_wrong"] = _s(tw.get("why_wrong"), "reasoning.tempting_wrong.why_wrong")
        rj = ro.get("rejected") or {}
        if free_reasoning:            # verdict changed: which option is tempting / rejected is the model's to restate
            if tw.get("option") not in d["options"]:
                raise ValueError("reasoning.tempting_wrong.option must be an option id")
            r["tempting_wrong"]["option"] = tw["option"]
            r["rejected"] = {k: _s(v, f"reasoning.rejected.{k}") for k, v in rj.items() if k in d["options"]}
        else:
            for oid in list(r["rejected"]):
                r["rejected"][oid] = _s(rj.get(oid), f"reasoning.rejected.{oid}")
        fo = out.get("flip") or {}
        fc = d["flip_conditions"]
        for key, field_ in (("would_change", "if"), ("would_not_change", "if"), ("watch_for", "what")):
            for w in fc.get(key, []):
                v = fo.get(w["id"])
                if not isinstance(v, dict):
                    raise ValueError(f"flip.{w['id']} missing")
                w[field_] = _s(v.get(field_), f"flip.{w['id']}.{field_}")
                w["why"] = _s(v.get("why"), f"flip.{w['id']}.why")
        d["lesson"] = _s(out.get("lesson"), "lesson")
        d["limits"] = _s(out.get("limits"), "limits")


def apply_structure(d: dict, out: dict, choice: str, orig_con_ids: list[str]):
    """Considerations edits (facts/favors/weight/rules_out/drop), new considerations, decisive. In place."""
    ct = out.get("considerations") or {}
    keep = []
    for c in d["considerations"]:
        u = ct.get(c["id"])
        if isinstance(u, dict):
            if u.get("drop"):
                continue
            for k in ("facts", "favors", "weight"):
                if k in u:
                    c[k] = u[k]
            if "rules_out" in u:
                if u["rules_out"]:
                    c["rules_out"] = u["rules_out"]
                else:
                    c.pop("rules_out", None)
        if not c["facts"]:
            raise ValueError(f"consideration {c['id']} cites no facts (a fact it rested on was removed): give it facts or drop it")
        keep.append(c)
    d["considerations"] = keep
    nxt = max([int(i[1:]) for i in orig_con_ids] + [int(c["id"][1:]) for c in keep], default=0)
    new_ids = []
    for nc in out.get("new_considerations") or []:
        nxt += 1
        item = {"id": f"C{nxt}", "facts": nc.get("facts"), "equity": nc.get("equity"), "favors": nc.get("favors"),
                "weight": nc.get("weight"), "why": nc.get("why")}
        if nc.get("rules_out"):
            item["rules_out"] = nc["rules_out"]
        if not (isinstance(item["facts"], list) and item["facts"] and isinstance(item["equity"], str) and item["favors"] is not None
                and item["why"]):
            raise ValueError("new_considerations entries need facts, equity, favors, weight, why")
        d["considerations"].append(item)
        new_ids.append(item["id"])
    ids = {c["id"] for c in d["considerations"]}
    dec = out.get("decisive") or (out.get("verdict") or {}).get("decisive")
    if not (isinstance(dec, list) and dec and all(x in ids for x in dec)):
        raise ValueError(f"decisive {dec!r} must be a non-empty list of consideration ids that still exist among {sorted(ids)}")
    fav = {c["id"]: c["favors"] for c in d["considerations"]}
    if not any(choice in fav[x] for x in dec):
        raise ValueError(f"at least one decisive consideration must favor the verdict option {choice}")
    d["verdict"]["decisive"] = dec
    d["verdict"]["choice"] = choice
    return new_ids


def finish_flip_conditions(d: dict, out: dict, choice: str, c_choice: str, fired: str | None = None, need_back: bool = False):
    """Drop would_change items made vacuous by the new verdict; reversal handled by caller; add new_would_change."""
    fc = d["flip_conditions"]
    keep = []
    for w in fc["would_change"]:
        if w["id"] == fired:
            w["then"] = c_choice
            keep.append(w)
        elif w["then"] != choice:
            keep.append(w)
    nxt = max([int(w["id"][4:]) for w in fc["would_change"]], default=0)
    for nw in out.get("new_would_change") or []:
        nxt += 1
        if not isinstance(nw, dict):     # model sometimes returns bare strings: reject with feedback, don't crash
            raise ValueError("each new_would_change entry must be an object {if, then, why}, not a string")
        if nw.get("then") not in d["options"] or not nw.get("if") or not nw.get("why"):
            raise ValueError("new_would_change entries need if, then (an option id), why")
        if nw["then"] == choice:
            raise ValueError(f"new_would_change `then` must differ from the verdict {choice} (an item that points at the verdict is vacuous)")
        keep.append({"id": f"flip{nxt}", "if": nw["if"], "then": nw["then"], "why": nw["why"]})
    if need_back and not any(w["then"] == c_choice for w in keep):
        raise ValueError(f"add a new_would_change whose then is {c_choice} (what would restore the parent's verdict)")
    if not keep:
        raise ValueError("flip_conditions would be empty: give new_would_change (what would restore the other option)")
    fc["would_change"] = keep


# ------------------------------------------------------------------ assembling X'
def option_spread(d: dict) -> float:
    n = [len(o["do"].split()) for o in d["options"].values()]
    return round(max(n) / max(1, min(n)), 2)


def build_scenario(X: Scenario, ctx: Ctx, op: str, tid: str, d: dict, tier: str, sk: Skeleton, detail: dict) -> Scenario:
    d = copy.deepcopy(d)
    d["id"] = tid
    d["title"] = f"{X.case.title} [{SHORT[op]}]"
    d["status"] = "needs_review"
    d["library"] = {"domain": X.domain, "family": X.family, "derived_from": X.id, "operator": op}
    case = Case.model_validate(d)
    fields = {"case.facts": f"{op}.facts", "case.verdict": "perturb.construct", "case.options": "perturb.construct"}
    ctx.prov.fields.update({k: v for k, v in fields.items()})
    return Scenario(id=tid, family=X.family, split=X.split, domain=X.domain, status="derived", case=case,
                    verdict_tier=tier, basis=f"derived by {op} from {X.id}", source=X.source,
                    fact_spans={k: v for k, v in sk.spans.items() if v}, tags=sorted(set(X.tags) | {op, "derived"}),
                    lineage=Lineage(parent=X.id, operator=op, detail=detail), provenance=ctx.prov)


def gold_from(X: Scenario, T: Scenario, sk: Skeleton, new_con: list[str], force_corresponding: set[str] = frozenset()):
    """Fact and consideration maps from the skeleton and the assembled T. force_corresponding: C consideration ids."""
    C, Tc = X.case, T.case
    g = GoldMap()
    for tid, org in sk.origin.items():
        if org == "new":
            g.live_only.append(Tc.global_id(tid))
        else:
            pair = GPair(live=Tc.global_id(tid), case=C.global_id(sk.t2c[tid]))
            (g.matched if org == "matched" else g.corresponding).append(pair)
    g.case_only = [C.global_id(c) for c, t in sk.c2t.items() if t is None]
    cm = GoldMap()
    tcons = {c.id: c for c in Tc.considerations}
    ccons = {c.id: c for c in C.considerations}
    for cid, c in ccons.items():
        if cid not in tcons:
            cm.case_only.append(C.global_id(cid))
            continue
        t = tcons[cid]
        remapped = [sk.c2t[f] for f in c.facts if sk.c2t.get(f)]
        changed = (t.facts != remapped or t.favors != c.favors or t.weight != c.weight or t.rules_out != c.rules_out
                   or cid in force_corresponding or any(sk.origin.get(f, "") == "corresponding" for f in t.facts)
                   or len(remapped) != len(c.facts))
        (cm.corresponding if changed else cm.matched).append(GPair(live=Tc.global_id(cid), case=C.global_id(cid)))
    cm.live_only = [Tc.global_id(c) for c in new_con]
    return g, cm


def kind_counts(X: Scenario, edits: list[Edit]) -> dict:
    out: dict[str, int] = {}
    kinds = {f.id: f.kind for f in X.case.facts}
    for e in edits:
        k = kinds.get(e.fact) if e.fact else (e.kind or "situation")
        out[k] = out.get(k, 0) + 1
    return out


def check_gold(C: Scenario, T: Scenario, p: dict):
    """Every C item and every T item accounted for exactly once; options total; via/choice consistent."""
    errs = []
    for label, cids, tids, gm in (("fact", [C.case.global_id(f.id) for f in C.case.facts], [T.case.global_id(f.id) for f in T.case.facts], p["fact_map"]),
                                  ("consideration", [C.case.global_id(f.id) for f in C.case.considerations],
                                   [T.case.global_id(f.id) for f in T.case.considerations], p["consideration_map"])):
        cs = [x.case for x in gm.matched + gm.corresponding] + gm.case_only
        ts = [x.live for x in gm.matched + gm.corresponding] + gm.live_only
        if sorted(cs) != sorted(cids):
            errs.append(f"{label}_map: C items not each accounted for once")
        if sorted(ts) != sorted(tids):
            errs.append(f"{label}_map: T items not each accounted for once")
    om = p["options_map"]
    if sorted(om) != sorted(T.case.global_id(o) for o in T.case.options):
        errs.append("options_map must cover every T option")
    if any(v is not None and v not in [C.case.global_id(o) for o in C.case.options] for v in om.values()):
        errs.append("options_map points outside C")
    if p["choice"] not in om:
        errs.append("choice is not a T option")
    if p["relation"] == "flips":
        w = {C.case.global_id(x.id): x for x in C.case.flip_conditions.would_change}
        via = p["via"][0] if p.get("via") else None
        if via not in w:
            errs.append("via is not a C would_change item")
        elif om.get(p["choice"]) != C.case.global_id(w[via].then):
            errs.append("flip choice is not the counterpart of the via item's then")
    if errs:
        raise OperatorError("gold map incomplete: " + "; ".join(errs))


def frame_same() -> FrameCmp:
    return FrameCmp(question="same", decider="same", role="same")


def identity_options(C: Scenario, T: Scenario) -> dict:
    return {T.case.global_id(o): C.case.global_id(o) for o in T.case.options}


def mean_surface_distance(X: Scenario, T: Scenario) -> float:
    from .overlap import jaccard
    cf = {f.id: f.fact for f in X.case.facts}
    xs = [1 - jaccard(cf[f.id], f.fact) for f in T.case.facts if f.id in cf]
    return round(sum(xs) / len(xs), 3) if xs else 0.0


def pilot_scenario(path, split="eval-only") -> Scenario:
    """Wrap a converted pilot case file as a Scenario (tests / live check only; P1's import_pilot is the real one)."""
    from bench.schema.pipeline import SourceRef
    p = Path(path)
    c = Case.load(p)
    return Scenario(id=c.id, family=c.library.get("family", c.id), split=split, domain=c.library.get("domain", "unknown"),
                    case=c, verdict_tier="source-endorsed", basis="pilot case (2b conversion)",
                    source=SourceRef(sha256=hashlib.sha256(p.read_bytes()).hexdigest(), doc="000000000000.jsonl"),
                    tags=["eval-only-import"])


def to_partial(**kw) -> dict:
    return kw


def dump_partial(p: dict) -> dict:
    out = {}
    for k, v in p.items():
        out[k] = v.model_dump(exclude_none=True) if hasattr(v, "model_dump") else v
    return out


def prose_fields(d: dict) -> dict[str, str]:
    r, fc = d["reasoning"], d["flip_conditions"]
    out = {"situation": d["situation"], "lesson": d["lesson"], "limits": d["limits"]}
    out.update({f"reasoning.{k}": r[k] for k in REASON})
    out["tw.pull"], out["tw.why"] = r["tempting_wrong"]["pull"], r["tempting_wrong"]["why_wrong"]
    out.update({f"rejected.{k}": v for k, v in r["rejected"].items()})
    out.update({f"C.{c['id']}": c["why"] for c in d["considerations"]})
    for key in ("would_change", "would_not_change", "watch_for"):
        out.update({f"{w['id']}.why": w["why"] for w in fc.get(key, [])})
    return out


def assemble(ctx: Ctx, X: Scenario, op: str, tid: str, d: dict, sk: Skeleton, tier: str, detail: dict, new_con: list[str],
             force_corr: set[str], relation: str, via, choice: str, touched, features: dict, intent: str, frame=None):
    """Build X' and the partial gold dict, run the completeness check."""
    ctx.code_step("perturb.construct", f"ids, options, verdict and gold maps built in code ({op})")
    T = build_scenario(X, ctx, op, tid, d, tier, sk, detail)
    fm, cm = gold_from(X, T, sk, new_con, force_corr)
    om = identity_options(X, T)
    partial = dict(intent=intent, case_scenario=X.id, trace_scenario=T.id, frame=frame or frame_same(), options_map=om,
                   fact_map=fm, consideration_map=cm, governs=True, relation=relation, via=via,
                   choice=T.case.global_id(choice), gold_tier=tier, touched=touched, distance_features=features,
                   provenance=T.provenance)
    check_gold(X, T, partial)
    return T, partial
