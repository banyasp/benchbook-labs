# M02 · Why no-case accuracy was 8-9% in pilot 1

**Status: COMPLETE.** This is a diagnosis of M01's control arm, done 2026-11-09. Most of the numbers are **Claude-read**:
ad-hoc Python queries plus Claude reading raw replies and traces in session `4e83879d`. No script was saved. The
inputs are on disk, so the numbers can be re-derived.

## What was measured
- **Question.** Why was Granite's no-case accuracy below chance? Is it the scorer (the reply schema failing to parse),
  or the data?
- **Population.** The control replies of M01, which were 72 when the diagnosis was done (80 by the end of the run);
  a store-wide count of the traces; and B2 grid control samples.

## What was observed
- **Breakdown of the 72 control replies:**
  - 4 had no parsable verdict (format).
  - 14 were off-menu because the reply framed a different, paperwork-level decision (O1).
  - 8 were off-menu with a borderline option match (judge score 0.1-0.5).
  - 40 were on-menu and wrong.
  - 6 were on-menu and right.
  The scorer is not the main cause.
- **The model is nearly deterministic per X1** (often 7 of 7 replies pick the same option), so the effective n is
  about 10 scenarios.
- **System-prompt authority cue.** In 5 of the 10 X1s, the trace's system prompt (message 0) stated a standing
  authority for a non-gold option. On those X1s, control was 0 of 38 for Granite and 0 of 40 for Luna; on the other 5,
  Granite got 6 of 40. Replies cite that authority as decisive.
- **Store-wide.** 319 of 589 live traces put an option in the system prompt, 218 of them a non-gold one.
- **B2 grid control by system-prompt option** (180 samples): gold 46%, none 36%, non-gold 39%. The cue does not
  always bite.
- **Leftover recommendations.** 109 of 589 live traces still carried an artificial recommendation, e.g. DR-AUT-001
  "I'd lean toward the hold".

## How
- **Breakdown.** Queries over `results/transfer/pilot1/samples.jsonl` (phase `control`) using `off_menu`,
  `parsed_choice` and `secondary`, plus the judge's option scores in `details/*.json`. Claude read the raw replies to
  assign the categories "paperwork decision" and "borderline match" and to confirm that replies cite the authority.
- **System-prompt option.** Uses the option spans the renderer recorded in each `trace.json` (`options[*].message ==
  0`), compared with the scenario's gold. This is deterministic, but the query was ad hoc.
- **LLMs.** Claude-read (classification of the off-menu replies). There is no LLM judge beyond what M01's scoring
  already used.
- **Data / examples.**
  - `results/transfer/pilot1/raw/base_control_DR-CORPUS-NS-7d5e5ea6-E6_v1_-_0.txt`: cites the authority.
  - `raw/base_control_DR-AUT-001_v1_-_1.txt`: follows the recommendation.
  - `raw/base_control_DR-CORPUS-NX-1fb1e4ff-E3_v1_-_2.txt`: borderline match.
  - Trace `data/store/traces/_versions/DR-CORPUS-CHILCOT-NX-249d4566-E59@v1.pre-render-v4-*/trace.json`, message 0:
    "HRD's standing delegation permits it to waive medical confirmation…".

## Key observations
- The cause was the trace, not the evaluator: the renderer's `system_scope` channel (render.v3, rule 2) wrote one
  course into the system prompt as a standing rule.
- This led to render.v4 and later (no course in the system prompt, the role owns the decision, the trace ends with a
  request for the decision) and to the framing gate (M04).
- Interpretation and risks: `docs/OBSERVATIONS.md` O14; `docs/RISK-REGISTER.md` R93 (and R91).
