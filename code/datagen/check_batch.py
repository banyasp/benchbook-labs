#!/usr/bin/env python3
"""Acceptance runner for a Benchbook data batch (spec v2.6): wraps mvp.py and adds batch-level checks.

BATCH_DIR holds case folders (<CASE>/ with *.reference.yaml, *.live.yaml, *.trace.json, *.reply.json).
Per folder: validate every card and live spec; require and check each live's trace (words 500-1200,
fact_share 0.10-0.25 enforced, leak scan); score each arm's reply (right card, every listed revised
card, the first decoy); check revised cards (same scenario, different choice, every rN listed on a
live). Per batch, and again with every --cumulative dir added: mvp floors, gold-letter spread,
hand-up and irreversible gold shares, gold-is-longest share, variant mix, PROPOSED LABEL on
novel/cross scenarios, and a table of option lengths.

Writes a Markdown report (summary table first) and a JSON twin next to it. Exit 1 on any error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bbcommon import load_mvp, words  # noqa: E402

WORDS_RANGE = (500, 1200)         # trace words before the card (spec 4, rule 5)
SHARE_RANGE = (0.10, 0.25)        # decisive-fact share of those words (rule 4)
TOTAL_SLACK = 0.05                # right-card arm: total >= maximum - slack
MIN_CONTROL_TOTAL = 1.55          # revised-card and decoy arms
HANDUP_MAX, IRREV_RANGE, FLIP_TRAP_MIN = 0.35, (0.15, 0.60), 0.40
FLOOR_MARGIN = 0.10               # a reasoning-free policy may beat chance by at most this
OPTION_WORDS = (12, 18)           # BRIEF-B001 balance rule (a warning here)
SCHEMA_WORDS = ["gold", "planted", "relation:", "move:", "irreversible", "partial", "signature", "variant",
                "would_change", "would_not_change", "PROPOSED LABEL", "golden", "partially"]
OPTION_MARKER = re.compile(r"(?mi)^\s*(?:option\s+)?[A-D][\).:]\s+\S")
REVISED_ID = re.compile(r"-r(\d+)$")
SKIP_DIRS = {"versions", "scratch", "_raw", "_dry", "__pycache__"}


# --------------------------------------------------------------------------
# Reusable checks (run_stage.py imports these). Each returns [(kind, message)] errors.
# --------------------------------------------------------------------------
def _snippet(text, i, n):
    return " ".join(text[max(0, i - 25): i + n + 25].split())


def leak_scan(trace, mvp):
    """Schema words, value ids, option-marker lines, consult/label strings in every message but the
    final injection (tool-call arguments included)."""
    msgs = trace.get("messages") or []
    last = msgs[-1] if msgs else {}
    injected = last.get("name") == "benchbook" or "{{CARD}}" in str(last.get("content", ""))
    out = []
    for i, m in enumerate(msgs[:-1] if injected else msgs):
        text = str(m.get("content") or "")
        for c in m.get("tool_calls") or []:
            text += "\n" + json.dumps(c, ensure_ascii=False)
        low = text.lower()
        for w in SCHEMA_WORDS:
            k = low.find(w.lower())
            if k >= 0:
                out.append(("leak", f"message {i}: schema word `{w}`: ...{_snippet(text, k, len(w))}..."))
        for v in sorted(mvp.VALUES):
            mt = re.search(rf"\b{re.escape(v)}\b", text)
            if mt:
                out.append(("leak", f"message {i}: value id `{v}`"))
        mt = OPTION_MARKER.search(text)
        if mt:
            out.append(("leak", f"message {i}: line starts with an option marker: `{mt.group(0).strip()}`"))
        if "benchbook.consult" in text:
            out.append(("leak", f"message {i}: mentions benchbook.consult"))
    return out


def strict_trace_check(trace, live, mvp):
    """mvp.check_trace plus the standards the spec treats as errors. -> (stats, errors, warnings)."""
    rep = mvp.Report("trace")
    stats = mvp.check_trace(trace, live, rep) or {}
    errors = [("trace", e) for e in rep.errors]
    warns = [w for w in rep.warnings if not w.startswith(("schema word", "trace is", "decisive quotes"))]
    if stats:
        n, share = stats["words"], stats["fact_share"]
        if not WORDS_RANGE[0] <= n <= WORDS_RANGE[1]:
            errors.append(("trace-words", f"{n} words before the card (required {WORDS_RANGE[0]}-{WORDS_RANGE[1]})"))
        if not SHARE_RANGE[0] <= share <= SHARE_RANGE[1]:
            errors.append(("fact-share", f"fact_share {share} (required {SHARE_RANGE[0]}-{SHARE_RANGE[1]})"))
    return stats, errors + leak_scan(trace, mvp), warns


def revised_card_errors(ref, rev):
    """A revised card keeps the reference's scenario exactly and changes the choice."""
    errs = []
    a, b = ref.get("scenario") or {}, rev.get("scenario") or {}
    if a != b:
        diff = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
        errs.append(("revised-card", f"scenario differs from the reference's in: {', '.join(diff)}"))
    if (rev.get("resolution") or {}).get("choice") == (ref.get("resolution") or {}).get("choice"):
        errs.append(("revised-card", "choice does not differ from the reference's"))
    return errs


def check_reply(reply, live, ref, kind, expect, mvp, trace=None):
    """Score one reply and apply the acceptance expectations for its arm (kind: right|revised|decoy).
    -> (summary dict, errors, warnings)."""
    errors, warns = [], []
    try:
        res = mvp.score_reply(reply, live, ref)
    except Exception as e:  # a malformed reply is a failed reply, never a crash
        return {"acted": None, "total": None, "ok": False}, [("reply", f"cannot score: {type(e).__name__}: {e}")], warns
    planted = bool((live.get("gold") or {}).get("planted"))
    summary = {"acted": res.get("acted"), "total": res.get("total"), "gate": res.get("gate")}
    if res.get("gate") != 1:
        errors.append(("reply", "format gate failed: " + "; ".join(res.get("errors") or ["unknown"])))
    if res.get("acted") not in expect:
        errors.append(("reply", f"tool calls match option {res.get('acted')}, expected {'/'.join(expect)}"))
    if res.get("gate") == 1:
        for part in ("relation", "fit") + (("differences",) if kind == "right" and planted else ()):
            if res.get(part) != 1.0:
                errors.append(("reply", f"{part} scored {res.get(part)} (expected 1.0)"))
        floor = (1.9 if planted else 1.6) - TOTAL_SLACK if kind == "right" else MIN_CONTROL_TOTAL
        if res["total"] < floor:
            errors.append(("reply", f"total {res['total']} below {floor:.2f}"))
    try:  # mapping warnings (length budget and the like) that score_reply drops
        m = reply.get("mapping")
        m = yaml.safe_load(m) if isinstance(m, str) else m
        rep = mvp.Report("mapping")
        mvp.check_mapping(m if isinstance(m, dict) and "mapping" in m else {"mapping": m}, rep, live, ref)
        warns += [("reply", w) for w in rep.warnings]
    except Exception:
        pass
    if trace:
        sysmsg = str((trace.get("messages") or [{}])[0].get("content", ""))
        for c in reply.get("tool_calls") or []:
            if isinstance(c, dict) and c.get("name") and c["name"] not in sysmsg:
                warns.append(("reply", f"calls tool `{c['name']}`, which the system prompt does not list"))
    summary["ok"] = not errors
    return summary, errors, warns


def arms_for(live):
    """The reply arms a live scenario must have: right card, each revised card, the first decoy."""
    g = live.get("gold") or {}
    want = g.get("acceptable") or [g.get("choice")]
    arms = [{"name": "right", "kind": "right", "file": f"{live['id']}.reply.json", "served": live.get("reference"), "expect": want}]
    for i, rc in enumerate(live.get("revised_cards") or []):
        m = REVISED_ID.search(str(rc.get("served")))
        tag = f"r{m.group(1)}" if m else f"r{i + 1}"
        arms.append({"name": tag, "kind": "revised", "file": f"{live['id']}.{tag}.reply.json",
                     "served": rc.get("served"), "expect": [rc.get("choice")]})
    if live.get("decoys"):
        arms.append({"name": "decoy", "kind": "decoy", "file": f"{live['id']}.decoy.reply.json",
                     "served": live["decoys"][0], "expect": want})
    return arms


# --------------------------------------------------------------------------
# Issue log
# --------------------------------------------------------------------------
class Issues:
    def __init__(self):
        self.items = []

    def add(self, level, kind, scope, msg):
        item = {"level": level, "kind": kind, "scope": scope, "msg": str(msg)}
        if item not in self.items:   # the same card served from two folders reports once
            self.items.append(item)

    def err(self, kind, scope, msg):
        self.add("error", kind, scope, msg)

    def warn(self, kind, scope, msg):
        self.add("warning", kind, scope, msg)

    def extend(self, level, scope, pairs):
        for kind, msg in pairs:
            self.add(level, kind, scope, msg)

    def of(self, level):
        return [i for i in self.items if i["level"] == level]


def read_json(path):
    with open(path) as f:
        return json.load(f)


# --------------------------------------------------------------------------
# One case folder
# --------------------------------------------------------------------------
def check_folder(folder, mvp, I):
    refs, lives, opt_rows = {}, {}, []
    for pattern, store in (("*.reference.yaml", refs), ("*.live.yaml", lives)):
        for p in sorted(folder.glob(pattern)):
            stem = p.name[: -len(pattern) + 1]
            try:
                rep = mvp.validate_file(str(p))
                doc = mvp.load(str(p))
            except Exception as e:
                I.err("validate", stem, f"{p.name}: cannot be read: {type(e).__name__}: {e}")
                continue
            I.extend("error", stem, [("validate", e) for e in rep.errors])
            I.extend("warning", stem, [("validate", w) for w in rep.warnings])
            if doc.get("id") != stem:
                I.err("validate", stem, f"{p.name}: id `{doc.get('id')}` does not match the file name")
            store[stem] = doc
            row = option_row(p.name, doc, I, stem)
            if row not in opt_rows:
                opt_rows.append(row)
            if store is lives and doc.get("variant") in ("novel", "cross") and "PROPOSED LABEL" not in p.read_text():
                I.err("label", stem, f"a {doc['variant']} scenario needs PROPOSED LABEL in its file")

    main = {i: d for i, d in refs.items() if not REVISED_ID.search(i)}
    revised = {i: d for i, d in refs.items() if REVISED_ID.search(i)}
    served_by = {rc.get("served") for d in lives.values() for rc in d.get("revised_cards") or []}
    live_refs = {d.get("reference") for d in lives.values()}
    decoys = {x for d in lives.values() for x in d.get("decoys") or []}
    cards = []
    for rid, ref in main.items():
        decoy_copy = rid in decoys and rid not in live_refs   # a served copy of another family's case
        rs = sorted(i for i in revised if i.rsplit("-r", 1)[0] == rid)
        if not decoy_copy:
            if not rs:
                I.err("revised-card", rid, f"no {rid}-rN.reference.yaml revised card in the folder")
            if rid not in live_refs:
                I.warn("batch", rid, "no live scenario in the folder serves this reference")
        for i in rs:
            I.extend("error", i, revised_card_errors(ref, revised[i]))
            if "illustrative" not in " ".join(map(str, (revised[i].get("provenance") or {}).get("caveats") or [])).lower():
                I.warn("revised-card", i, "caveats do not mark the card as illustrative, not Peter's view")
        cards.append({"id": rid, "choice": ref["resolution"].get("choice") if isinstance(ref.get("resolution"), dict) else None,
                      "card_words": _card_words(ref, mvp), "revised": rs, "decoy_copy": decoy_copy})
    for i, rev in revised.items():
        base = i.rsplit("-r", 1)[0]
        if base not in main:
            I.err("revised-card", i, f"no base reference {base}.reference.yaml in the folder")
        if i not in served_by:
            I.err("revised-card", i, "not listed in revised_cards on any live scenario in the folder")

    rows = []
    for lid, live in lives.items():
        rows.append(check_live_files(folder, lid, live, refs, mvp, I))
    return rows, cards, opt_rows


def _card_words(doc, mvp):
    try:
        return words(mvp.card(doc))
    except Exception:
        return None


def check_live_files(folder, lid, live, refs, mvp, I):
    row = {"id": lid, "variant": live.get("variant"), "words": None, "fact_share": None, "arms": {}}
    g = live.get("gold") or {}
    om = g.get("option_map")
    served = [live.get("reference")] + [rc.get("served") for rc in live.get("revised_cards") or []] + list(live.get("decoys") or [])
    for cid in dict.fromkeys(x for x in served if x):
        if cid not in refs:
            I.err("missing-card", lid, f"served card {cid}.reference.yaml is not in the folder (mvp.py would skip its checks)")
    for rc in live.get("revised_cards") or []:   # the revised answer must be the revised card's own choice
        card = refs.get(rc.get("served"))
        if card and isinstance(card.get("resolution"), dict):
            mapped = (om or {}).get(rc.get("choice"), rc.get("choice")) if om else rc.get("choice")
            if mapped != card["resolution"].get("choice"):
                I.err("revised-card", lid, f"revised_cards choice {rc.get('choice')} maps to {mapped}, but {rc['served']}'s choice is {card['resolution'].get('choice')}")

    trace = None
    tp = folder / f"{lid}.trace.json"
    if not tp.exists():
        I.err("missing-trace", lid, f"{tp.name} not found")
    else:
        try:
            trace = read_json(tp)
            stats, errs, warns = strict_trace_check(trace, live, mvp)
            row["words"], row["fact_share"] = stats.get("words"), stats.get("fact_share")
            I.extend("error", lid, errs)
            I.extend("warning", lid, [("trace", w) for w in warns])
        except Exception as e:
            I.err("trace", lid, f"{tp.name}: {type(e).__name__}: {e}")
        if not (folder / f"{lid}.trace.md").exists():
            I.warn("trace", lid, f"{lid}.trace.md not found (make it with mvp.py trace-view)")

    arms = arms_for(live)
    for arm in arms:
        cell = row["arms"][arm["name"]] = {"acted": None, "total": None, "ok": False, "present": False}
        rp = folder / arm["file"]
        if not rp.exists():
            I.err("missing-reply", lid, f"{arm['file']} not found ({arm['name']} arm)")
            continue
        if arm["served"] not in refs:
            continue   # missing-card already reported
        cell["present"] = True
        try:
            summary, errs, warns = check_reply(read_json(rp), live, refs[arm["served"]], arm["kind"], arm["expect"], mvp, trace)
        except Exception as e:
            summary, errs, warns = {"acted": None, "total": None, "ok": False}, [("reply", f"{type(e).__name__}: {e}")], []
        cell.update(summary)
        I.extend("error", lid, [(k, f"{arm['name']} arm: {m}") for k, m in errs])
        I.extend("warning", lid, [(k, f"{arm['name']} arm: {m}") for k, m in warns])
    expected = {a["file"] for a in arms}
    for p in sorted(folder.glob(f"{lid}.*reply.json")):
        if re.fullmatch(re.escape(lid) + r"\.(?:r\d+\.|decoy\.)?reply\.json", p.name) and p.name not in expected:
            I.warn("reply", lid, f"{p.name} has no matching revised_cards/decoys entry in the live spec")
    row["_scopes"] = {x for x in [lid, live.get("reference")] + served if x}
    return row


# --------------------------------------------------------------------------
# Option lengths and balance (per file)
# --------------------------------------------------------------------------
def option_problems(doc):
    """(words per option, gold letter, [balance problems]) for a reference or live doc. The BRIEF-B001
    rules: 12-18 words, no commas or semicolons, the same number of "and" in every option, gold never
    the longest (not applied to revised cards, whose options are the reference's)."""
    gold = (doc.get("resolution") or {}).get("choice") if "resolution" in doc else (doc.get("gold") or {}).get("choice")
    opts = (doc.get("scenario") or {}).get("options") or {}
    do = {k: str((o or {}).get("do", "")) for k, o in opts.items()}
    w = {k: words(t) for k, t in do.items()}
    probs = []
    if len(w) > 1 and gold in w and not REVISED_ID.search(str(doc.get("id"))) and w[gold] >= max(w.values()):
        probs.append(f"gold option {gold} is the longest ({w[gold]} words; ties count)")
    out = [f"{k}={n}" for k, n in w.items() if not OPTION_WORDS[0] <= n <= OPTION_WORDS[1]]
    if out:
        probs.append(f"option lengths outside {OPTION_WORDS[0]}-{OPTION_WORDS[1]} words: {', '.join(out)}")
    punct = [k for k, t in do.items() if "," in t or ";" in t]
    if punct:
        probs.append(f"commas or semicolons in option {', '.join(punct)}")
    ands = {k: len(re.findall(r"\band\b", t)) for k, t in do.items()}
    if len(set(ands.values())) > 1:
        probs.append(f"uneven use of 'and' across options ({ands})")
    return w, gold, probs


def option_row(name, doc, I, scope):
    w, gold, probs = option_problems(doc)
    for p in probs:
        I.warn("balance", scope, f"{name}: {p}")
    return {"file": name, "words": w, "gold": gold}


# --------------------------------------------------------------------------
# Batch-level balance
# --------------------------------------------------------------------------
def collect(root):
    """Reference and live files under root, skipping versions/scratch folders."""
    out = []
    for p in sorted(Path(root).rglob("*.yaml")):
        rel = p.relative_to(root).parts[:-1]
        if (p.name.endswith(".reference.yaml") or p.name.endswith(".live.yaml")) and not (set(rel) & SKIP_DIRS):
            out.append(p)
    return out


def analyze(paths, mvp):
    """Balance statistics over the unique decisions in paths, plus [(kind, message)] flags."""
    decs = {}
    for p in paths:
        try:
            doc = mvp.load(str(p))
            k = mvp.kind_of(doc)
            if k == "reference" and not REVISED_ID.search(str(doc["id"])):
                decs.setdefault(doc["id"], ("reference", None, doc["scenario"]["options"], doc["resolution"]["choice"], None))
            elif k == "live":
                decs.setdefault(doc["id"], ("live", doc.get("variant"), doc["scenario"]["options"], doc["gold"]["choice"],
                                            doc["gold"].get("relation")))
        except Exception:
            continue
    decs = {i: d for i, d in decs.items() if d[3] in d[2]}
    n = len(decs)
    stats = {"decisions": n}
    flags = []
    if not n:
        return stats, flags
    chance = sum(1 / len(d[2]) for d in decs.values()) / n
    gold_opt = lambda d: d[2][d[3]] or {}  # noqa: E731
    lens = lambda d: {k: words((o or {}).get("do")) for k, o in d[2].items()}  # noqa: E731
    letters = Counter(d[3] for d in decs.values())
    stats.update({
        "chance": round(chance, 3),
        "gold_letters": {k: round(letters[k] / n, 3) for k in sorted(letters)},
        "handup_gold_share": round(sum(gold_opt(d).get("move") in ("ask", "partial") for d in decs.values()) / n, 3),
        "irreversible_gold_share": round(sum(bool(gold_opt(d).get("irreversible")) for d in decs.values()) / n, 3),
        "gold_longest_share": round(sum(lens(d)[d[3]] >= max(lens(d).values()) for d in decs.values()) / n, 3),
    })
    lv = [d for d in decs.values() if d[0] == "live"]
    variants = Counter(d[1] for d in lv)
    stats["variants"] = dict(variants)
    if lv:
        stats["flip_trap_share"] = round((variants["flip"] + variants["trap"]) / len(lv), 3)
        # Copy-the-card baseline (training handoff, risk 1): share of lives whose gold simply follows the card.
        stats["follows_share"] = round(sum(d[4] == "follows" for d in lv) / len(lv), 3)
        # Most-specific-signature policy (training handoff, risk 2): matching rewards the most specific option, so a
        # policy that "does the most" wins wherever the gold has the most specific signature. Ties count 1/k.
        def spec(o):
            sig = (o or {}).get("signature") or {}
            return len(sig.get("calls") or []) * 2 + len(sig.get("without") or [])
        sv = []
        for d in lv:
            sp = {k: spec(o) for k, o in d[2].items()}
            if not any(sp.values()):
                continue
            top = [k for k, v in sp.items() if v == max(sp.values())]
            sv.append((1 / len(top) if d[3] in top else 0.0, 1 / len(d[2])))
        if sv:
            stats["floor_most_specific_signature"] = round(sum(a for a, _ in sv) / len(sv), 3)
            live_chance = sum(c for _, c in sv) / len(sv)
            if stats["floor_most_specific_signature"] > live_chance + FLOOR_MARGIN:
                flags.append(("floors", f"policy `most specific signature` scores {stats['floor_most_specific_signature']} against "
                                        f"chance {round(live_chance, 3)} on rendered lives (limit chance + {FLOOR_MARGIN})"))
    uniq = list(dict.fromkeys(str(p) for p in paths))
    try:
        stats["floors"] = {k: v for k, v in mvp.floors(uniq).items() if k not in ("decisions", "chance")}
    except Exception as e:
        flags.append(("batch", f"mvp floors could not run: {type(e).__name__}: {e}"))
        stats["floors"] = {}
    for k, v in stats["floors"].items():
        if v > chance + FLOOR_MARGIN:
            flags.append(("floors", f"policy `{k}` scores {v} against chance {round(chance, 3)} (limit chance + {FLOOR_MARGIN})"))
    if n >= 6 and max(letters.values()) / n > 0.45:
        top = letters.most_common(1)[0]
        flags.append(("balance", f"gold letter {top[0]} is {top[1] / n:.0%} of {n} decisions; spread letters evenly"))
    if stats["handup_gold_share"] > HANDUP_MAX:
        flags.append(("balance", f"hand-up golds are {stats['handup_gold_share']:.0%} of decisions (warn above {HANDUP_MAX:.0%})"))
    lo, hi = IRREV_RANGE
    if not lo <= stats["irreversible_gold_share"] <= hi:
        flags.append(("balance", f"irreversible golds are {stats['irreversible_gold_share']:.0%} (want {lo:.0%}-{hi:.0%})"))
    if stats["gold_longest_share"] > chance:
        flags.append(("balance", f"gold is the longest option in {stats['gold_longest_share']:.0%} of decisions, above chance {chance:.0%}"))
    if lv and stats.get("follows_share", 0) > 0.6:
        flags.append(("balance", f"{stats['follows_share']:.0%} of live golds follow the card; copying the card would score that much (want at most 60%)"))
    if lv and stats["flip_trap_share"] < FLIP_TRAP_MIN:
        flags.append(("balance", f"flip + trap are {stats['flip_trap_share']:.0%} of live scenarios (want at least {FLIP_TRAP_MIN:.0%})"))
    return stats, flags


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------
def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c).replace("|", "/") for c in r) + " |" for r in rows]
    return "\n".join(out)


def arm_cell(c):
    if c is None:
        return "-"
    if not c.get("present"):
        return "missing"
    total = "?" if c.get("total") is None else f"{c['total']:.2f}"
    return f"{c.get('acted')} {total}" + ("" if c.get("ok") else " BAD")


def render_markdown(result):
    s, I = result["summary"], result["issues"]
    arm_names = sorted({a for r in result["lives"] for a in r["arms"]}, key=lambda a: (a != "right", a == "decoy", a))
    L = [f"# Batch check: {result['batch']}", "",
         f"{s['lives']} live scenarios, {s['passed']} PASS, {s['lives'] - s['passed']} FAIL. "
         f"{s['errors']} errors, {s['warnings']} warnings. Validator: `{result['mvp']}`.", "",
         "## Summary", "",
         md_table(["Live", "Variant", "Words", "Fact share"] + [a if a != "right" else "Right card" for a in arm_names] + ["Errors", "Result"],
                  [[r["id"], r["variant"], r["words"] if r["words"] is not None else "-",
                    r["fact_share"] if r["fact_share"] is not None else "-"]
                   + [arm_cell(r["arms"].get(a)) for a in arm_names] + [r["errors"], r["result"]] for r in result["lives"]]), "",
         "Arm cells read `acted total`; BAD marks an arm that missed its expectation.", ""]
    for level, title in (("error", "Errors"), ("warning", "Warnings")):
        items = [i for i in I if i["level"] == level]
        L += [f"## {title} ({len(items)})", ""]
        L += [f"- `{i['scope']}` [{i['kind']}] {i['msg']}" for i in items] or ["None."]
        L.append("")
    if result["cards"]:
        L += ["## Cards", "", md_table(["Reference", "Choice", "Card words", "Revised cards", "Note"],
              [[c["id"], c["choice"], c["card_words"], ", ".join(c["revised"]) or "none",
                "served copy (decoy)" if c["decoy_copy"] else ""] for c in result["cards"]]), ""]
    L += ["## Batch balance", ""]
    b, c = result["batch_stats"], result.get("cumulative_stats")
    keys = ["decisions", "chance", "gold_letters", "handup_gold_share", "irreversible_gold_share",
            "gold_longest_share", "variants", "flip_trap_share", "follows_share", "floor_most_specific_signature"]
    fkeys = sorted((b.get("floors") or {}) | ((c or {}).get("floors") or {}))
    rows = [[k, json.dumps(b.get(k)), json.dumps(c.get(k)) if c else "-"] for k in keys]
    rows += [[f"floor: {k}", (b.get("floors") or {}).get(k, "-"), (c.get("floors") or {}).get(k, "-") if c else "-"] for k in fkeys]
    L += [md_table(["Metric", "Batch", "Cumulative"], rows), ""]
    L += ["## Option lengths (words per option; `*` marks the gold option)", ""]
    letters = sorted({k for r in result["option_lengths"] for k in r["words"]})
    L += [md_table(["File"] + letters, [[r["file"]] + [f"{r['words'][k]}{'*' if k == r['gold'] else ''}" if k in r["words"] else "" for k in letters]
                                          for r in result["option_lengths"]]), ""]
    return "\n".join(L)


def run(batch_dir, cumulative, mvp_arg=None):
    mvp = load_mvp(mvp_arg)
    batch = Path(batch_dir)
    I = Issues()
    folders = [p for p in sorted(batch.iterdir()) if p.is_dir() and p.name not in SKIP_DIRS and not p.name.startswith(".")]
    if any(batch.glob("*.live.yaml")) or any(batch.glob("*.reference.yaml")):
        folders.insert(0, batch)
    lives, cards, opt_rows = [], [], []
    for f in folders:
        r, c, o = check_folder(f, mvp, I)
        lives += r
        cards += c
        opt_rows += o
    errs_by_scope = Counter(i["scope"] for i in I.items if i["level"] == "error")
    for r in lives:   # a live fails on its own errors and on errors in the cards it serves
        r["errors"] = sum(errs_by_scope[s] for s in r.pop("_scopes"))
        r["result"] = "FAIL" if r["errors"] else "PASS"
    paths = collect(batch)
    bstats, flags = analyze(paths, mvp)
    for kind, msg in flags:
        (I.err if kind == "floors" else I.warn)(kind, "batch", msg)
    cstats = None
    if cumulative:
        cpaths = list(paths)
        for d in cumulative:
            if not Path(d).is_dir():
                I.warn("batch", "cumulative", f"{d} is not a directory")
            cpaths += collect(d)
        cstats, cflags = analyze(cpaths, mvp)
        for kind, msg in cflags:
            I.warn(kind, "cumulative", msg)   # the cumulative set only warns
    errors, warnings = I.of("error"), I.of("warning")
    result = {"batch": str(batch), "mvp": mvp.__benchbook_path__, "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
              "summary": {"lives": len(lives), "passed": sum(r["result"] == "PASS" for r in lives),
                          "errors": len(errors), "warnings": len(warnings),
                          "errors_by_kind": dict(Counter(i["kind"] for i in errors))},
              "lives": lives, "cards": cards, "issues": I.items, "batch_stats": bstats,
              "cumulative_stats": cstats, "option_lengths": opt_rows}
    return result


TRAINING_REFUSED = re.compile(r"claude|anthropic|\bgpt-(?!oss)", re.I)


def training_gate(batch_dir, mvp):
    """--training: a batch bound for training needs signed-off cards and open-weight authorship (spec 2, 10)."""
    out = []
    for p in collect(batch_dir):
        try:
            doc = mvp.load(str(p))
        except Exception:
            continue
        k = mvp.kind_of(doc)
        drafted = str(((doc.get("provenance") or {}).get("drafted_by")) or "")
        if k == "reference" and doc.get("status") != "signed_off":
            out.append({"level": "error", "scope": str(doc.get("id")), "kind": "training",
                        "msg": f"{p.name}: status is `{doc.get('status')}`; only cards Peter has signed off may seed training data"})
        if TRAINING_REFUSED.search(drafted):
            out.append({"level": "error", "scope": str(doc.get("id")), "kind": "training",
                        "msg": f"{p.name}: drafted_by `{drafted}` is not an allowed training-bound author (spec 10)"})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batch_dir", metavar="BATCH_DIR", help="folder of case folders")
    ap.add_argument("--cumulative", nargs="+", action="extend", default=[], metavar="DIR",
                    help="earlier batches; the balance checks rerun on batch + these (floors only warn there)")
    ap.add_argument("--mvp", help="path to mvp.py (default: env BENCHBOOK_MVP, then $BENCHBOOK_LABS/ideas/...)")
    ap.add_argument("--out", metavar="REPORT.md", help="write the Markdown report here and a JSON twin beside it (else print)")
    ap.add_argument("--training", action="store_true",
                    help="the batch is bound for training: require signed-off cards and open-weight authorship")
    args = ap.parse_args(argv)
    if not Path(args.batch_dir).is_dir():
        ap.error(f"{args.batch_dir} is not a directory")
    try:
        result = run(args.batch_dir, args.cumulative, args.mvp)
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if args.training:
        extra = training_gate(args.batch_dir, load_mvp(args.mvp))
        result["issues"] = extra + result["issues"]
        result["summary"]["errors"] += len(extra)
    md = render_markdown(result)
    if args.out:
        out = Path(args.out)
        out.write_text(md + "\n")
        out.with_suffix(".json").write_text(json.dumps(result, indent=2, default=list) + "\n")
        s = result["summary"]
        print(f"{s['passed']}/{s['lives']} lives PASS, {s['errors']} errors, {s['warnings']} warnings -> {out}")
    else:
        print(md)
    return 1 if result["summary"]["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
