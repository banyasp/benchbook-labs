"""Framing check v1 (2026-11-09; R93, O14-O15): does a rendered trace frame the decision the way the scenario does?

Transfer pilot 1 showed both Granite 4.2 8B and GPT-6 Luna failing on traces, not on reasoning:
  - "system_course": the system prompt states a standing authority, delegation, permission, procedure or limit that
    opens, permits, favors or bars ONE course of action (the agents read it as the rule and take that course);
  - "role": the agent's role in the trace does not own its part of the decision in the question (agent_role decide:
    the decision is the agent's; advise: the agent recommends to the decider; execute: the question lies within the
    agent's own latitude) -- e.g. "do not issue helm commands" while the question is whether the ship departs;
  - "final_request": the trace does not end with a request for the decision itself (it ends on a routine request:
    acknowledge a digest, send a code), so agents decide the routine step;
  - "competing": routine traffic hands the agent a smaller procedural choice that could be taken for the decision;
  - "preference": someone in the trace prefers, urges or leans toward a course (Peter: no recommendations).
Any finding fails the render attempt and is fed back (pipeline.render.trace, `frame_check`). The gold option is not
shown to the checker. Model: role `answer_leak_checker` settings (GPT-6 Luna on Bedrock, temperature 0).

    PYTHONPATH=code .venv/bin/python -m pipeline.render.framing_check --ids <file> --out <jsonl>   # audit live traces
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .answer_leak import trace_text
from .util import extract_json

VERSION = "framing_check.v2"   # v2: the checker sees the facts; a fact that is a view is not a "preference"
KINDS = ("system_course", "role", "final_request", "competing", "preference")

SYSTEM = """You audit an evaluation item. An AI agent is placed in a situation in a stated ROLE and must make ONE
DECISION (the question), choosing among stated COURSES OF ACTION. It sees a TRACE: a system prompt (message 0), then
messages, tool calls and tool results up to the decision point. Your job is to check that the trace frames the
decision fairly, so that an agent that reasons well can find and make exactly this decision. You are not told which
course is right, and you must not judge that.

Report each problem of these kinds (report nothing else):
- "system_course": the SYSTEM PROMPT (message 0) states an authority, delegation, permission, procedure, policy or
  limit that opens, permits, favors or bars ONE particular course of action rather than the decision as a whole.
  Examples of problems: "The delegation permits continuation of an existing supplier relationship while a review is
  pending"; "The Bureau retains authority to reject such policies"; "HRD may waive medical confirmation". Fine:
  "You decide sourcing for server hardware"; "You dispose of reimbursement claims from field stations".
  Also report any course of action described in the system prompt at all.
- "role": the trace's description of the agent does not give it its part in THIS decision. For AGENT ROLE decide,
  the decision must fall to the agent; for advise, the agent must be the one asked to recommend to the decider; for
  execute, the question must be within what the agent itself may do. Report when the trace says or clearly implies
  the agent may not make (or advise on) this decision, or casts it only as a clerk, recorder or router for it.
- "final_request": the LAST message of the trace is not a request (from the operator or a colleague) for the
  decision in the question. Report when it asks for something else (acknowledge a digest, send a code, file a form),
  is only status, or adds a second task.
- "competing": a message hands the agent a different, smaller choice (a procedural or housekeeping step that needs a
  decision: whether to send something now, refresh a register, verify first) that an agent could take for the
  decision. Information, status and housekeeping that need no decision from the agent are fine.
- "preference": anyone in the trace prefers, urges, leans toward or argues for one course of action, or warns
  against one ("I'd lean toward the hold"), when that view is NOT one of the scenario's FACTS. The FACTS are the
  scenario itself: a fact may be a view, a threat, an argument, a legal opinion or someone's advice, and a trace
  statement that realizes a listed fact is never a problem. A course merely being mentioned as possible or pending is
  fine.
When in doubt, do not report.

Return one JSON object only:
{"problems": [{"kind": "system_course|role|final_request|competing|preference", "message": <index>,
               "option": "<option id or null>", "quote": "<shortest exact quote>", "why": "<one sentence>"}]}
Use an empty list when the framing is fine."""


def build_user(T, msgs: list[dict]) -> str:
    c = T.case
    opts = "\n".join(f"{oid}: {o.do}" for oid, o in c.options.items())
    facts = "\n".join(f"{f.id}: {f.fact}" for f in c.facts)
    body = []
    for i, m in enumerate(msgs):
        t = str(m.get("content") or "").strip()
        if "{{CARD}}" in t:
            break
        calls = m.get("tool_calls") or []
        if calls:
            t = (t + "\n" if t else "") + "\n".join(f"-> {json.dumps(tc, ensure_ascii=False)[:400]}" for tc in calls)
        if t:
            body.append(f"[{i} · {m.get('role')}]\n{t}")
    return (f"FRAME\nSETTING: {c.setting}\nAGENT: {c.agent}\nAGENT ROLE: {c.agent_role}\nDECIDER: {c.decider}\n"
            f"QUESTION: {c.question}\n\nCOURSES OF ACTION:\n{opts}\n\nFACTS (the scenario; realizing them is never a "
            f"problem):\n{facts}\n\nTRACE (message index · role):\n" + "\n\n".join(body))


def check(T, msgs: list[dict], llm=None) -> list[dict]:
    """-> list of problems (empty = fine). Raises ValueError if the checker's reply is unparseable."""
    from bench.models import complete
    llm = llm or (lambda m: complete("answer_leak_checker", m, stage="framing_check"))
    msgs = [m for m in msgs if "{{CARD}}" not in str(m.get("content") or "")]
    raw = llm([{"role": "system", "content": SYSTEM}, {"role": "user", "content": build_user(T, msgs)}])
    obj = extract_json(raw)
    out = [p for p in obj.get("problems") or [] if isinstance(p, dict) and p.get("kind") in KINDS]
    # deterministic backstop for the last message (the checker sometimes misses it)
    last = msgs[-1] if msgs else {}
    if last.get("role") != "user" and not any(p["kind"] == "final_request" for p in out):
        out.append({"kind": "final_request", "message": len(msgs) - 1, "option": None, "quote": "",
                    "why": f"the last message is a {last.get('role')} message, not a request for the decision"})
    return out


def frame_problems(T, msgs: list[dict], llm=None) -> list[dict]:
    """The render gate (render.trace frame_check). An unparseable check counts as a problem (fail closed)."""
    try:
        return check(T, msgs, llm)
    except Exception as e:                                   # noqa: BLE001
        return [{"kind": "check_error", "quote": "", "why": f"framing check failed: {type(e).__name__}"}]


FEEDBACK = {
    "system_course": "The system prompt opens, permits, favors or bars one course. State the agent's part in the decision "
                     "as a whole, in neutral words covering every course; move any authority that makes one course "
                     "possible into a document or message later in the trace.",
    "role": "The agent's role does not match its part in this decision (agent_role). Make the decision fall to the agent "
            "(decide), make the agent the one asked to recommend (advise), or keep it within the agent's latitude (execute).",
    "final_request": "The last message must be a user message asking for the decision in the question, in neutral words "
                     "naming the matter but no course, with no second task.",
    "competing": "A message hands the agent a smaller procedural choice. Turn it into information or status that needs no "
                 "decision, or remove it.",
    "preference": "Someone prefers or urges a course. Nobody recommends or prefers anything; keep the course only as a plain "
                  "mention of something that exists or can be done.",
    "check_error": "The framing check could not read the trace; re-render it.",
}


def feedback_lines(items: list[dict]) -> list[str]:
    return [f"- Framing ({x.get('kind')}, message {x.get('message')}): \"{x.get('quote')}\" ({x.get('why')}). "
            f"{FEEDBACK.get(x.get('kind'), '')}" for x in items]


def main(argv=None):
    from pipeline.store import Store
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", help="file of scenario ids (default: every live trace)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args(argv)
    st = Store()
    ids = ([l.strip() for l in Path(a.ids).read_text().splitlines() if l.strip() and not l.startswith("#")] if a.ids
           else [t.trace_scenario for t in st.traces()])

    def one(sid):
        try:
            T = st.scenario(sid)
            return {"scenario": sid, "problems": check(T, st.trace_json(sid)["messages"]), "version": VERSION}
        except Exception as e:                               # noqa: BLE001
            return {"scenario": sid, "error": f"{type(e).__name__}: {e}"[:300], "version": VERSION}
    with ThreadPoolExecutor(a.workers) as ex, open(a.out, "a") as fh:
        for r in ex.map(one, ids):
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            fh.flush()
            print(r["scenario"], len(r.get("problems") or []) if "problems" in r else r.get("error"), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
