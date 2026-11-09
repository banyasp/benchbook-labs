"""Human review sheet for the answer-leak checks (Peter, 2026-11-09: a quote alone can't be judged without the question,
the agent's role and the decider).

    PYTHONPATH=code .venv/bin/python -m pipeline.render.leak_review --out results/allpairs/LEAK-REVIEW-2026-11-09.md

One entry per flagged scenario (every check file `results/allpairs/answer-leak-v*-*.jsonl` that flagged it), with:
who the agent is, its role, the decider, the question, the options (gold marked), the flagged fact (full text) or the
trace quote in context, the checker's reading (who decided, why), and what was done: fact rewrite (before -> after),
re-render, re-check result, final status.
"""
from __future__ import annotations

import argparse
import glob
import json
import re
from pathlib import Path

from pipeline.store import Store

ROOT = Path("results/allpairs")


def load_jsonl(pattern: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for p in sorted(glob.glob(str(ROOT / pattern))):
        for line in Path(p).read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                r["_file"] = Path(p).name
                out.setdefault(r["scenario"], []).append(r)
    return out


def trace_context(store: Store, sid: str, quote: str, width: int = 260) -> str | None:
    """The quote with surrounding text, from the trace as it was when flagged (quarantined copies first)."""
    if not quote:
        return None
    cands = sorted(glob.glob(str(store.root / "traces" / "_leaked" / f"{sid}*" / "*.json")))
    cands += [str(store.trace_dir(sid) / "trace.json")]
    q = quote.strip().strip('"')[:80]
    for c in cands:
        try:
            msgs = json.loads(Path(c).read_text())["messages"]
        except Exception:                                    # noqa: BLE001
            continue
        for i, m in enumerate(msgs):
            t = str(m.get("content") or "")
            k = t.find(q)
            if k >= 0:
                a, b = max(0, k - width), min(len(t), k + len(quote) + width)
                snippet = ("…" if a else "") + t[a:b] + ("…" if b < len(t) else "")
                snippet = re.sub(r"\s+", " ", snippet).replace(q, f"**{q}**", 1)
                return f"[message {i}, {m.get('role')}] {snippet}"
    return None


def entry(store: Store, sid: str, checks: list[dict], fixes: list[dict]) -> list[str]:
    T = store.scenario(sid)
    c = T.case
    gold = c.verdict.choice
    old_fact: dict[str, str] = {}
    for f in fixes:
        old_fact.update(((f.get("fact_fix") or {}).get("old")) or {})
    L = [f"### {sid}", "",
         f"**{c.title}** — {T.domain}", "",
         f"- **Agent:** {c.agent}  \n  **Agent's role:** {c.agent_role}  \n  **Decider:** {c.decider}",
         f"- **Question:** {c.question}",
         "- **Options** (★ = gold):"]
    for oid, o in c.options.items():
        L.append(f"  - {'★ ' if oid == gold else ''}{oid}: {o.do}")
    for ch in checks:
        if not ch.get("leak"):
            continue
        ver = ch.get("check", "v2")
        for x in ch.get("frame") or []:
            L.append(f"- **Flag ({ver}, frame field `{x.get('field')}`, {x.get('kind')}; points at {x.get('option') or 'no option'}"
                     f"{' = gold' if x.get('option_is_gold') else ''}):** \"{x.get('quote')}\"  \n"
                     f"  Checker: decided by *{x.get('who')}* — {x.get('why')}")
        for x in ch.get("facts") or []:
            fid = x.get("id")
            text = old_fact.get(fid) or next((f.fact for f in c.facts if f.id == fid), "?")
            L.append(f"- **Flag ({ver}, fact {fid}, {x.get('kind')}; points at {x.get('option') or 'no option'}"
                     f"{' = gold' if x.get('option_is_gold') else ''}):** \"{text}\"  \n"
                     f"  Checker: decided by *{x.get('who')}* — {x.get('why')}")
        for x in ch.get("trace") or []:
            ctx = trace_context(store, sid, x.get("quote") or "")
            L.append(f"- **Flag ({ver}, trace, {x.get('kind')}; points at {x.get('option') or 'no option'}"
                     f"{' = gold' if x.get('option_is_gold') else ''}):** \"{x.get('quote')}\"  \n"
                     f"  Checker: decided by *{x.get('who')}* — {x.get('why')}"
                     + (f"  \n  In context: {ctx}" if ctx else ""))
    for f in fixes:
        ff = f.get("fact_fix") or {}
        for fid in ff.get("edited") or []:
            L.append(f"- **Fix (fact {fid}):** \"{ff['old'][fid]}\"  \n  → \"{ff['new'][fid]}\"")
        rc = f.get("recheck") or {}
        L.append(f"- **Result ({f['_file']}):** trace re-rendered: {f.get('render') or '—'}"
                 + (f" ({f.get('render_reason')})" if f.get("render_reason") else "")
                 + (f"; re-check: {'still leaks' if rc.get('leak') else 'clean'}" if rc else "")
                 + f" → **{f.get('final')}**")
    live = store.has_trace(sid)
    L += [f"- **Now:** {'in use (trace live)' if live else 'OUT (quarantined or dropped)'}", ""]
    return L


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "LEAK-REVIEW-2026-11-09.md"))
    a = ap.parse_args(argv)
    store = Store()
    checks = load_jsonl("answer-leak-v[234]-*.jsonl")
    fixes = load_jsonl("unleak*-*.jsonl")
    flagged = sorted(s for s, rs in checks.items() if any(r.get("leak") for r in rs))
    corpus = [s for s in flagged if s.startswith("DR-CORPUS")]
    older = [s for s in flagged if not s.startswith("DR-CORPUS")]
    n_live = sum(store.has_trace(s) for s in flagged)
    L = ["# Answer-leak review sheet (2026-11-09)", "",
         "Every scenario the role-aware leak check flagged, with what the agent is deciding, so a flag can be judged. "
         "**Definition (Peter, 2026-11-09):** a leak is a fact or trace statement that THIS decision was already made or "
         "carried out by the agent, by whoever holds its role, or by the decider it acts for (unless the agent is allowed "
         "to adapt that earlier plan to changed circumstances), or an authoritative statement of what happened after the "
         "decision point (warnings and forecasts are fine). A different body's decision under review is not a leak.", "",
         "Checks: v2 = role-aware; v3 = v2 plus the two caveats (prior plan the agent may adapt; outcome = authoritative "
         "future); v4 = v3 plus the frame fields (title, setting, situation, decider), which can also carry the decision. The checker is GPT-6 Luna and is not perfectly consistent run to run, which is why a trace that passed "
         "once can be flagged on a later check. What to look for: a flag that is NOT a leak (the check is too broad), or "
         "a fix that still gives the answer away (the fix is too lenient).", "",
         f"**{len(flagged)} scenarios flagged** ({len(corpus)} corpus, {len(older)} older set); {n_live} are back in use "
         "after a fix and a clean re-check, the rest are out.", "",
         "Each entry: agent, role, decider, question, options (★ = gold); each flag with the checker's reading; the fix "
         "(fact before → after); the result.", "",
         f"## Corpus scenarios ({len(corpus)})", ""]
    for s in corpus:
        L += entry(store, s, checks[s], fixes.get(s, []))
    L += [f"## Older (2f) scenarios ({len(older)})", ""]
    for s in older:
        L += entry(store, s, checks[s], fixes.get(s, []))
    Path(a.out).write_text("\n".join(L) + "\n")
    print(a.out, len(flagged))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
