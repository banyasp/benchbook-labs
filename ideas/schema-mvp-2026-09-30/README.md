# Benchbook MVP schema: reference case and mapping (2026-09-30)

A deliberately simple schema for the MVP experiment: one decider, one decision, 2-4 options,
3-6 considerations, with the judgment carried in short prose (read, weighing, tradecraft,
uncertainty, handoff, tempting wrong answer, lesson, limits) around a thin checkable spine.
The agent's mapping has five moves: frame, fit, compare, carry, decide.

- Schema doc (design, templates, worked example, scoring, fit test, decisions):
  https://claude.ai/code/artifact/b7f38f3b-d3ce-4b10-837b-bd448b1b6237
- Examples doc (13 cases, 20 live scenarios, 22 mappings, one tab per case):
  https://claude.ai/code/artifact/a1b4c7f5-ca1b-4827-a3f6-22e4261d0633

## Layout

| Path | What it holds |
|---|---|
| `templates/` | Current templates (v2.5): `reference`, `live`, `mapping`, and `TRACE-FORMAT.md` (how a live spec becomes the agent's context) |
| `code/mvp.py` | Validator, served-card renderer (full and spine), variant labeler, scorer |
| `examples/` | The worked example in the schema doc: AUT-001 reference, AUT-101 live scenario and mapping |
| `examples-v24/` | Three live specs rendered as agent traces (AUT-101, INT-103-v01, AGT-201-v01): spec with `render` and signatures, `trace.json`, the agent's-eye `trace.md`, gold `reply.json`, NOTES.md |
| `examples-v21/` | The 13 example cases, one folder each (reference, live scenarios, mappings, earlier drafts in `versions/`), plus `BRIEF.md` given to the drafting agents |
| `fit-test/` | The first fit test: six Hard Calls converted under v1 (`a1`-`a3`, with LOG.md misfit logs), migrated copies in `v2/`, and `BRIEF.md` |
| `review/` | The adversarial review of v2 (`REVIEW.md`), its policy probes and adversarial mappings |
| `versions/` | Snapshots: `v1/` (first draft), `v2/` (after the fit test); the long first AUT-001 draft |

## Run it

Needs Python 3.10+ and `pyyaml`.

```bash
python3 code/mvp.py validate examples-v21/*/*.yaml
python3 code/mvp.py card examples-v21/AUT-001/AUT-001.reference.yaml          # full card
python3 code/mvp.py card examples-v21/AUT-001/AUT-001.reference.yaml --spine  # ablation card
python3 code/mvp.py score examples-v21/AUT-001/AUT-101.mapping.yaml \
    examples-v21/AUT-001/AUT-101.live.yaml examples-v21/AUT-001/AUT-001.reference.yaml
python3 code/mvp.py trace-view examples-v24/AUT-101/AUT-101.trace.json --card examples-v24/AUT-101/AUT-001.reference.yaml
python3 code/mvp.py reply-score examples-v24/AUT-101/AUT-101.reply.json \
    examples-v24/AUT-101/AUT-101.live.yaml examples-v24/AUT-101/AUT-001.reference.yaml
python3 code/mvp.py floors examples-v21/*/*.yaml   # shortcut policies
```

## Status

Prototype. All case text was drafted by Claude agents; judgment prose, novel-variant golds
(marked PROPOSED LABEL) and [UNVERIFIED] citations need Peter's sign-off. Under the plan-v2
authorship rule this is prototype and eval material, not training data.
