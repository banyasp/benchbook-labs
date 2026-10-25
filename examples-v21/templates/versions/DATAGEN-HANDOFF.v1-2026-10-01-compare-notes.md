# Handoff: MVP schema changes → data generation pipeline (2026-10-01)
# (v1, superseded the same day: Peter ruled the schema authoritative; see ../DATAGEN-SPEC.md. Condensed record: items 1-11 and A-G are abridged from the project doc as first written.)

From the schema session to the "data generation" session. Peter asked the two of us to compare notes. Please read this, check it against your pipeline, and **append your reply in the last section of this doc** (project_read it, add your notes, project_write it back). I'll read it from there. I can't see your session's files, so the "likely affects" list is based on `claude/benchbook-real-data-sources.md` (plan v2, 2026-09-29). It may be out of date; correct it where it is.

## Where the current schema lives (Peter's Mac, edit in place, no zips)
- `~/Desktop/AI/benchbook-labs/examples-v21/templates/`: reference v2.3, live v2.5, mapping v2.5, TRACE-FORMAT.md v2.6. These are the spec.
- `~/Desktop/AI/benchbook-labs/examples-v21/<CASE>/`: 13 example cases; AUT-101, INT-103-v01, AGT-201-v01 fully rendered.
- Validator: `~/Desktop/AI/benchbook-labs/ideas/schema-mvp-2026-09-30/code/mvp.py`.
- Schema doc: https://claude.ai/code/artifact/b7f38f3b-d3ce-4b10-837b-bd448b1b6237

## What changed (Peter's decisions, 2026-09-30 / 10-01)
1. Shape of a reference case: one decider, one decision, 2-4 options, 3-6 considerations (neutral ids c1..., favors a list never all, value from the 28 equities, strong|weak|bar with rules_out, one-sentence why); choice, basis, decisive, rests_on; judgment prose read/weighing/tradecraft/uncertainty/handoff/tempting_wrong/rejected; lesson, limits; boundaries would_change (>=1, no cap), would_not_change, watch_for.
2. Autonomy by default; hand up only what the agent lacks authority to settle; "escalate when no close case" is an optional deployer setting.
3. No separate time field.
4. Card ~1,000-word ceiling (AUT-001 is 888).
5. Stakes spelled out in intrinsic terms (AUT-001: 23 ships, ~1,900 sailors, ~3 days).
6. Live YAML is the authoring spec; rendered into an agent trace (chat messages, 500-1,200 words before the card, decisive 10-25%, no menu, no schema words).
7. The case is injected by the harness (message role user, name benchbook, labeled reference material, {{CARD}}); no consult tool.
8. Arms swap only that message: right / revised / decoy / none.
9. Strict tool-call matching via option signatures; unmatched = wrong (-1, -2 if irreversible); option_map live -> card.
10. Mapping v2.5: frame, fit, compare, new (<=4), carry, decide (course, confidence, now, would_change_my_mind); no decide.choice.
11. Shortcut floors (34 decisions, chance 29%): most clauses 62%, longest 59%, never-irreversible 47%, always hand-up 38%; fixes listed.

## Likely effects on the data generation pipeline (please check)
A. Size targets conflict (plan v2: exemplar ~200 words, <=3 served; live 1.5-4k tokens, 5-9 documents, decisive 15-25% -> 8-12%) vs MVP (card <=1,000 words, one served; trace 500-1,200 words, decisive 10-25%). Framed as "Peter needs to rule".
B. Hand-up share: Hard Calls 72/100 partial; keep hand-ups a minority.
C. Live specs need render, signatures, tools covering every option, option_map, revised_cards, decoys, injected ending.
D. No cross-case factor ids; solver per value + weight; offered an optional `factor:` field.
E. Hard Calls v1 -> MVP field map.
F. Quality gate: validate, floors, trace-check, reply-score.
G. Unchanged: terms-of-use / authorship rule.

## Open questions on the schema side
- AUT-001 crew aboard as a consideration; partial -> act + routes; given:/unless:.

## Reply from the data generation session
(asked for: what your pipeline assumes, what conflicts, what you need changed in the schema)
