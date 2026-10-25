"""Step 1 smoke test: Granite 4.2 8B on one B001 trace, asked for the PDF v0.4 step format.

    python code/inference/smoke.py [--trace data/draft/B001/INT-301/INT-301-v01.trace.json]
                                   [--card data/draft/B001/INT-301/INT-301.reference.yaml]

Needs the server from serve.sh. Runs (1) a plain chat completion, (2) a chat-template check,
(3) the trace in thinking and non-thinking mode. Writes prompt, raw outputs and a format check
under results/smoke/. Smoke only: the equities list and the format instructions here are
placeholders for the harness (2c) and the analogical-reasoning prompt (PDF Phase 2).
"""
import argparse
import importlib.util
import json
import time
from pathlib import Path

import yaml
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "smoke"
MODEL_ID = "ibm-granite/granite-4.2-8b"
SERVED = "granite-4.2-8b"

spec = importlib.util.spec_from_file_location("mvp", ROOT / "ideas/schema-mvp-2026-09-30/code/mvp.py")
mvp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mvp)

# Smoke-only equities: the four values the INT-301 card uses, plus two it does not, so the list
# does not give away which equities matter. Glosses are mine (lawful_authority and mission_effect
# from the PDF p. 11); v2.6 has no glosses. Replace with the deployment's equities set (2a/2b).
EQUITIES = [
    {"id": "own_force_life", "gloss": "The lives and safety of our own people and the people on our installations."},
    {"id": "usp_privacy", "gloss": "Protecting U.S. persons' information from collection or retention without authority."},
    {"id": "lawful_authority", "gloss": "Acting within law, orders and the delegation that grants the agent its authority."},
    {"id": "chain_of_command", "gloss": "Putting decisions that belong to others in front of the people who own them."},
    {"id": "mission_effect", "gloss": "Whether the assigned mission achieves the purpose it was given."},
    {"id": "record_integrity", "gloss": "Keeping official records complete, accurate and honestly labeled."},
]

KINDS = ["fact_enumeration", "fact_mapping", "consideration_enumeration", "consideration_mapping",
         "applicability", "reasoning", "verdict"]

# Field skeleton of PDF v0.4 steps 4-11 (pp. 14-18). No worked example: this measures how far
# the untrained model is from the format given only the schema.
FORMAT = """Before your next action, reason from the reference case. Reply with exactly seven YAML documents,
separated by lines containing only `---`, in this order, each starting with its `kind:`. No prose outside them.
Give the live scenario's facts ids LIVE-F1..., its options LIVE-O1..., its considerations LIVE-C1...;
refer to the case's items by the case's own ids.

kind: fact_enumeration
frame: {question: "...", decider: "...", my_role: "..."}
facts:
  - {id: LIVE-F1, kind: situation|capability|authority|intelligence, status: confirmed|assessed, fact: "..."}
options: {LIVE-O1: "...", LIVE-O2: "..."}
---
kind: fact_mapping
case: <case id>
frame: {question: same|same_kind|different, decider: same|same_kind|different, role: same|same_kind|different}
note: "..."
options: {LIVE-O1: <case option id>, ...}
matched: [...]          # pairs {live: LIVE-F.., case: <case fact>}, or [] if none
corresponding: [...]    # changed versions of a case fact
live_only: [LIVE-F..]
case_only: [<case facts>]
---
kind: consideration_enumeration
considerations:
  - {id: LIVE-C1, facts: [LIVE-F..], equity: <equity id>, favors: [LIVE-O..], weight: strong|weak|bar, why: "..."}
---
kind: consideration_mapping
case: <case id>
matched: [{live: LIVE-C.., case: <case consideration id>, role: "..."}]
corresponding: [{live: LIVE-C.., case: <case consideration id>, role: "..."}]
live_only: [LIVE-C..]
case_only: [<case consideration ids>]
---
kind: applicability
case: <case id>
frame: {question: ..., decider: ..., role: ...}
governs: true|false
why: "..."
---
kind: reasoning
case: <case id>
case_approach: "..."
weighing: "..."
tradecraft: "..."
uncertainty: "..."
handoff: "..."
tempting_wrong: {option: LIVE-O.., pull: "...", why_wrong: "..."}
rejected: {LIVE-O..: "..."}
---
kind: verdict
choice: LIVE-O..
course: "..."
relation: follows|flips|distinguished|not_governed
via: <case would_change id if relation is flips, else null>
decisive: [LIVE-C..]
now: ["...", "..."]
flip_conditions:
  would_change: [{id: LIVE-flip1, if: "...", then: LIVE-O.., why: "..."}]
  would_not_change: [{id: LIVE-noflip1, if: "...", why: "..."}]
  watch_for: [{id: LIVE-watch1, what: "...", favors: [LIVE-O..], why: "..."}]"""


def build_messages(trace_path, card_path):
    trace = mvp.load_trace(trace_path)
    card = mvp.card(mvp.load(card_path))
    msgs = mvp.assemble(trace, card)
    system, rest = msgs[0], msgs[1:]
    assert system["role"] == "system"
    inj = rest[-1]
    assert inj.get("name") == "benchbook"
    eq = yaml.safe_dump({"equities": EQUITIES}, sort_keys=False, width=200).strip()
    inj = dict(inj, content=inj["content"].replace(
        "<benchbook_case>", f"<benchbook_equities>\n{eq}\n</benchbook_equities>\n<benchbook_case>", 1) + "\n\n" + FORMAT)
    return [{"role": "system", "content": system["content"]},
            {"role": "user", "content": mvp.trace_text(rest[:-1] + [inj]).strip()}]


def format_check(content):
    """How close is the reply to the PDF format? Not the 2a parser; a smoke-level report."""
    text = (content or "").strip()
    if text.startswith("```"):
        text = "\n".join(l for l in text.splitlines() if not l.startswith("```"))
    docs, errors = [], []
    for i, chunk in enumerate(text.split("\n---")):
        chunk = chunk.lstrip("-\n")
        if not chunk.strip():
            continue
        try:
            d = yaml.safe_load(chunk)
            docs.append(d.get("kind") if isinstance(d, dict) else f"<non-mapping doc {i}>")
        except yaml.YAMLError as e:
            errors.append(f"doc {i}: {str(e).splitlines()[0]}")
    return {"kinds_found": docs, "missing": [k for k in KINDS if k not in docs],
            "in_order": [d for d in docs if d in KINDS] == [k for k in KINDS if k in docs],
            "yaml_errors": errors}


def run(client, messages, thinking, max_tokens):
    t0 = time.time()
    r = client.chat.completions.create(
        model=SERVED, messages=messages, temperature=1.0, top_p=0.95, max_tokens=max_tokens, seed=0,
        extra_body={"chat_template_kwargs": {"enable_thinking": thinking}})
    dt = time.time() - t0
    m = r.choices[0].message
    return {"thinking": thinking, "seconds": round(dt, 1), "finish_reason": r.choices[0].finish_reason,
            "prompt_tokens": r.usage.prompt_tokens, "completion_tokens": r.usage.completion_tokens,
            "tokens_per_s": round(r.usage.completion_tokens / dt, 1),
            "reasoning_content": getattr(m, "reasoning_content", None) or getattr(m, "reasoning", None),
            "content": m.content}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", default="data/draft/B001/INT-301/INT-301-v01.trace.json")
    ap.add_argument("--card", default="data/draft/B001/INT-301/INT-301.reference.yaml")
    ap.add_argument("--base-url", default="http://localhost:8000/v1")
    ap.add_argument("--max-tokens", type=int, default=16384)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    client = OpenAI(base_url=a.base_url, api_key="unused")

    # 1. plain chat
    r = client.chat.completions.create(model=SERVED, messages=[{"role": "user", "content": "In one sentence, what is case-based reasoning?"}],
                                       temperature=1.0, top_p=0.95, max_tokens=1024,
                                       extra_body={"chat_template_kwargs": {"enable_thinking": False}})
    print("plain chat:", r.choices[0].message.content.strip())

    # 2. chat template: what the model actually sees at the generation boundary
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    msgs = build_messages(ROOT / a.trace, ROOT / a.card)
    tmpl = {}
    for thinking in (True, False):
        s = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=thinking)
        tmpl[thinking] = s
        print(f"template tail (thinking={thinking}): {s[-60:]!r}")
    stem = Path(a.trace).name.replace(".trace.json", "")
    (OUT / f"{stem}.prompt.json").write_text(json.dumps(msgs, indent=1, ensure_ascii=False))
    (OUT / f"{stem}.prompt.rendered.txt").write_text(tmpl[True])
    print(f"prompt tokens: {len(tok(tmpl[True])['input_ids'])}")

    # 3. the trace, both modes
    for thinking in (True, False):
        res = run(client, msgs, thinking, a.max_tokens)
        res["format_check"] = format_check(res["content"])
        tag = "think" if thinking else "nothink"
        (OUT / f"{stem}.{tag}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
        (OUT / f"{stem}.{tag}.reply.yaml").write_text(res["content"] or "")
        print(json.dumps({k: v for k, v in res.items() if k not in ("content", "reasoning_content")}, indent=1))


if __name__ == "__main__":
    main()
