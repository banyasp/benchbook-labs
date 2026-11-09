"""Answer-leak check, v3 (role-aware; Peter's definition and caveats, 2026-11-09). Checks a scenario's FACTS and its rendered TRACE.

The agent acts in a role (Q: agent, agent_role) for a decider (Q: decider) and faces one question. A LEAK is:
  - decided: the facts or the trace say that THIS decision has already been made (or carried out) by the agent itself,
             by whoever holds the agent's role, or by the decider it acts for. E.g. the agent is the committee and the
             trace says "the committee decided not to investigate".
  - outcome: they describe what happened after this decision was taken (which option was carried out and its result),
             or judge an option with hindsight.
NOT a leak: a decision by a different entity in a different role that the agent may review, uphold or overrule (an
appeal, an audit of a lower body); recommendations, requests, advice, proposals, drafts awaiting sign-off, anyone
arguing for an option, a course being available; background events before the decision point.

Leaky traces are never used (Peter): a fact-level leak means the scenario must be fixed (the fact edited or dropped,
then re-rendered); a trace-only leak means the trace is re-rendered. This module only detects; see
`results/allpairs/LEAKS-2026-11-09.md` for what was done.

    PYTHONPATH=code .venv/bin/python -m pipeline.render.answer_leak --ids <file> --out <jsonl>

Model: role `answer_leak_checker` (GPT-6 Luna on Bedrock). The gold option is not shown to the checker.
v1 (role-blind, trace only): versions/answer_leak.v1-role-blind.py. v2 (role-aware, before Peter's two caveats: a decider's
prior plan is fine when the agent may adapt it; outcomes = authoritative future, not warnings): versions/answer_leak.v2-role.py.
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pipeline.store import Store

from .util import extract_json

SYSTEM = """You audit an evaluation item. An AI agent is placed in a situation in a stated ROLE and must make one
DECISION (the question). It sees a TRACE (messages and documents up to the decision point). The trace was written from
a list of FACTS. Neither may give the decision away.

A LEAK is one of:
- "decided": a statement that THIS decision has already been made or carried out, by the agent itself, by whoever
  holds the agent's role (the same office, committee, post), or by the decider the agent acts for.
  Example: the agent IS the review committee, and the text says "the committee decided not to investigate".
  Exception: if the agent is explicitly asked or allowed to reconsider, adapt or deviate from a prior plan or
  direction because circumstances have changed (e.g. the boss said "here is what I want, but pivot if things change"),
  then stating that prior plan or the decider's earlier wish is NOT a leak.
- "outcome": an authoritative statement of what happens AFTER the decision point (which course was carried out and
  how it turned out), or a hindsight judgment of a course of action. The trace describes only the past and the
  present; it cannot know the future. Warnings, forecasts, intelligence that something is about to happen, and
  predictions are NOT outcomes.

NOT a leak (never flag these):
- a decision by a DIFFERENT entity in a different role that the agent may now review, uphold or overrule
  (e.g. the agent hears an appeal of a lower body's decision; the agent audits another office's choice);
- recommendations, requests, advice, proposals, orders being sought, drafts or forms awaiting approval, anyone arguing
  for a course of action, a course being available or permitted;
- background events that happened before the decision point, including earlier, different decisions;
- a prior plan or the decider's earlier direction, when the agent is asked or allowed to adapt it to new circumstances;
- warnings, forecasts or advance intelligence about what may happen next.
When in doubt, do not flag.

Check the FACTS list and the TRACE separately. Return one JSON object only:
{"facts": [{"id": "<fact id>", "kind": "decided" | "outcome", "who": "<who made the decision, as stated>",
            "option": "<option id it points to, or null>", "why": "<one sentence>"}],
 "trace": [{"kind": "decided" | "outcome", "who": "<...>", "option": "<option id or null>",
            "quote": "<shortest exact quote>", "why": "<one sentence>"}]}
Use empty lists when there is no leak."""


def trace_text(msgs: list[dict]) -> str:
    out = []
    for i, m in enumerate(msgs[1:], 1):
        c = str(m.get("content") or "").strip()
        if "{{CARD}}" in c:
            break
        calls = m.get("tool_calls") or []
        if calls:
            c = (c + "\n" if c else "") + "\n".join(f"-> {json.dumps(tc, ensure_ascii=False)[:400]}" for tc in calls)
        if c:
            out.append(f"[{i} · {m.get('role')}]\n{c}")
    return "\n\n".join(out)


def build_user(T, msgs: list[dict] | None) -> str:
    c = T.case
    opts = "\n".join(f"{oid}: {o.do}" for oid, o in c.options.items())
    facts = "\n".join(f"{f.id}: {f.fact}" for f in c.facts)
    sys_prompt = str(msgs[0].get("content") or "")[:3000] if msgs else ""
    return (f"AGENT: {c.agent}\nAGENT ROLE: {c.agent_role}\nDECIDER: {c.decider}\nQUESTION: {c.question}\n\n"
            f"COURSES OF ACTION:\n{opts}\n\nFACTS:\n{facts}\n\n"
            + (f"TRACE SYSTEM PROMPT:\n{sys_prompt}\n\nTRACE:\n{trace_text(msgs)}" if msgs else "TRACE: (none rendered)"))


def check(T, msgs: list[dict] | None, llm=None) -> dict:
    """-> {"facts": [...], "trace": [...]} (each item marked option_is_gold), or raises ValueError if unparseable."""
    from bench.models import complete
    llm = llm or (lambda m: complete("answer_leak_checker", m, stage="answer_leak"))
    raw = llm([{"role": "system", "content": SYSTEM}, {"role": "user", "content": build_user(T, msgs)}])
    obj = extract_json(raw)
    gold = T.case.verdict.choice
    mark = lambda xs: [dict(x, option_is_gold=(x.get("option") == gold) if x.get("option") else None) for x in xs or []]
    return {"facts": mark(obj.get("facts")), "trace": mark(obj.get("trace"))}


def trace_leaks(T, msgs: list[dict], llm=None) -> list[dict]:
    """The render gate (render.trace leak_check): trace leaks only. An unparseable check counts as a leak (fail closed)."""
    try:
        return check(T, msgs, llm)["trace"]
    except Exception as e:                                   # noqa: BLE001
        return [{"kind": "check_error", "quote": "", "why": f"leak check failed: {type(e).__name__}"}]


def check_one(store: Store, sid: str, llm=None) -> dict:
    T = store.scenario(sid)
    msgs = store.trace_json(sid)["messages"] if store.has_trace(sid) else None
    try:
        r = check(T, msgs, llm)
    except Exception as e:                                   # noqa: BLE001
        return {"scenario": sid, "error": f"unparseable: {e}"[:200]}
    fl, tl = r["facts"], r["trace"]
    return {"scenario": sid, "check": "v3-role-latitude", "leak": bool(fl or tl), "where": ("facts" if fl else ("trace" if tl else None)),
            "facts": fl, "trace": tl, "gold": T.case.verdict.choice,
            "agent": T.case.agent, "decider": T.case.decider, "question": T.case.question, "has_trace": msgs is not None}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", required=True, help="file of scenario ids")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args(argv)
    ids = [l.strip() for l in Path(a.ids).read_text().splitlines() if l.strip() and not l.startswith("#")]
    store = Store()
    out = Path(a.out)
    done = {json.loads(l)["scenario"] for l in out.read_text().splitlines() if l.strip()} if out.exists() else set()
    todo = [s for s in ids if s not in done]

    def one(sid):
        try:
            return check_one(store, sid)
        except Exception as e:                               # noqa: BLE001
            return {"scenario": sid, "error": f"{type(e).__name__}: {e}"[:300]}

    n = leaks = 0
    with ThreadPoolExecutor(a.workers) as ex, open(out, "a") as fh:
        for r in ex.map(one, todo):
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            fh.flush()
            n += 1
            leaks += bool(r.get("leak"))
    print(json.dumps({"checked": n, "leaks": leaks, "skipped_done": len(done)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
