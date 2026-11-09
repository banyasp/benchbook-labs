# Option matching (the verdict translator): spot check and tuning, 2026-11-09

The verdict is scored by translating the base model's chosen option to the answer key's options (the model words
and orders its own options), then exact-matching. The translation is Jev Choice in both directions (which generated
option is this gold option; which gold option is this generated option), combined by geometric mean S, paired
greedily above a threshold. Peter asked for 0.7 to start, a hand spot check, and tuning if it did not match.

## What the spot check showed

- 8 random B2 samples, mapped by hand and compared with Jev (instruction v1): Jev's pairing agreed in all 8,
  including reordered options (Tet, Pearl Harbor, Cuban Missile Crisis E1-7561), unmatched extra options, and a reply
  whose "options" were paperwork steps rather than the decision (no match, correctly).
- Raising the threshold from 0.5 to 0.7 changed 6 of 189 verdicts, all from right to wrong, and in all 6 the match
  was real (e.g. "Approve the proposed arrangements: ..." vs "The senior MOD official approves the proposed
  arrangements ..." at S = 0.64).
- S is bimodal (580 cells < 0.1, 288 > 0.8), but 40 cells sit in 0.2-0.7, and most of those are real matches. Cause:
  the v1 option instruction asks for "the same act, through the same channel or recipient, at the same time", and
  the base model's options carry trace-level detail (routing, docket copies, extra steps) that the decision-level
  answer key does not, so Jev puts much of its mass on "none of these".

## Tuning

Labelled set: 32 cells labelled by hand (the 0.2-0.7 band; ambiguous ones left out) plus 116 cells from the same
28 samples labelled by their v1 score (>= 0.7 match, < 0.2 no match); 53 matches. Instruction v2 for options asks for
the same core choice and ignores implementation detail (text: `code/scorers/prompts/instructions.v2.yaml`).

| instruction | threshold | real matches found (of 53) | false matches |
|---|---|---|---|
| v1 | 0.7 | 26 | 0 |
| v1 | 0.5 | 39 | 1 |
| v1 | 0.3 | 48 | 2 |
| **v2** | **0.5** | **51** | **0** |
| v2 | 0.6 | 47 | 0 |
| v2 | 0.7 | 43 | 0 |

Hand-labelled band only (27 matches, 4 non-matches): v1 at 0.7 finds 0; v2 at 0.5 finds 25 with 0 false matches.

Held-out check: 12 other B2 samples, read by hand against v2's pairing: all 12 agree (reorders, unmatched extra
options, two replies whose options were paperwork steps, one borderline: "do not sign the release; review each
record" vs "continues the group's detention", S = 0.17, unmatched).

## Decision

Judge prompts v2 (only the option instruction changed; fact, consideration, frame instructions are v1's text, so
their cached calls stay valid) and option threshold 0.5. Facts and considerations keep 0.5. Recorded per sample as
`scoring` in samples.jsonl; B2 re-scored (`python -m eval.allpairs rescore`). Every sample now keeps every score row
and the full Jev output (R, C, S matrices per step) in `details/`, so a different threshold can be re-applied later
without generating again.

Files: `option-judge-tuning/` (labelled cells with v1 and v2 S, the band list, the two scripts).
