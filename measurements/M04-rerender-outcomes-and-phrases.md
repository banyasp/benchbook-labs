# M04 · Re-rendering traces (render.v4 → v5): gate outcomes and cloned closing lines

**Status: COMPLETE.** The re-renders ran on 2026-11-09 between 21:59 and 23:11 UTC. The phrase counts were redone with
a saved script on 2026-11-10.

## What was measured
1. How many traces pass the gates when re-rendered with the new framing rules.
2. Whether the final request in the re-rendered traces became a stock formula: a cue shared across traces, and odd
   prose.

## What was observed

**Re-render outcomes:**

| Log | Prompt | Traces | ok | Rejected (still failing a gate after retries) |
|---|---|---|---|---|
| `results/render/rerender-v4-20261109.jsonl` | render.v4 | 110 | 97 | 13 |
| `results/render/rerender-v5-20261109.jsonl` | render.v5 (pilot 1 X1s) | 10 | 9 | 1 |
| `results/render/rerender-v5b-20261109.jsonl` | render.v5 (all live traces) | 589 | 535 | 54 (9%) |

- **Rejected traces are not live.** They are in `data/store/traces/_rejected/`; the log's `reason`, `framing` and
  `answer_leak` fields say why. The pre-re-render versions are in `data/store/traces/_versions/<id>.<tag>-<ts>/`.
- **render.v4 closing lines (O17).** Of the first 97 v4 traces, 81 ended with "disposition" and 68 began "Please
  give…", cloned from the prompt's single quoted example. **Claude-read / ad-hoc query** at the time. These traces are
  no longer live (now in `_versions/*.pre-render-v5*`).
- **render.v5 closing lines (O18), re-counted 2026-11-10 with the saved script over the 535 live v5 traces:**
  - Contain "your call": 281 (195 "what's your call", 55 with a curly apostrophe).
  - Contain "what do you want": 124.
  - Contain "how do you want": 59.
  - Contain "disposition", "please give your" or "routing pass": 0.
  - Start with "what's your call", by the script's rule (whole message or last sentence): 218 (173 + 45). O18 reported
    199 (37%) from an earlier ad-hoc query with a narrower rule. The script's number is the reproducible one.

## How
- **Re-render.** `PYTHONPATH=code .venv/bin/python -m pipeline.render.rerender --ids <file> --tag <tag> --log <jsonl>`
  (`code/pipeline/render/rerender.py`). It calls `pipeline.render.trace.render_one`, with both gates on by default.
- **LLMs.**
  - Renderer: GPT-6 Luna, temperature 0.7.
  - Framing gate: GPT-6 Luna, temperature 0, `framing_check.v2`, plus deterministic stock-phrase and question-template
    checks.
  - Answer-leak gate: GPT-6 Luna, temperature 0.
  - Gate verdicts are LLM judgments.
- **Phrase counts.** `.venv/bin/python code/eval/analysis/final_request_phrases.py --render render.v5`. It is
  deterministic, with no LLM: substring counts on the last non-harness message.

## Key observations
- **Cloning.** A single quoted example in a generation prompt gets cloned into most outputs, and so do examples
  labelled "good". render.v6 therefore gives no quoted examples. Recorded in `CLAUDE.md` ("Trace framing") and in the
  "Lessons" section of the render prompt.
- **The "your call" lines were kept.** They carry no information about which option is right, so they were treated as
  a style monoculture, not an answer cue.
