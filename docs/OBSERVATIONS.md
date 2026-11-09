# Observations log

Interesting things noticed while running the pipeline: model behavior, data patterns, judge behavior. Kept next to
`RISK-REGISTER.md`, which records the *risks* (failure modes and what to do about them). An observation that turns
into a risk gets an R-number there and a pointer here. Every entry names its primary sources (sample ids, raw reply
files, scenario files, reports) so it can be re-read. Raw replies and judge matrices live on the box only
(`results/allpairs/<run>/raw/`, `details/`; not in git). Newest first. Started 2026-11-09 at Peter's request.

Paths below are relative to the repo root on the box (`/home/ubuntu/benchbook-labs`).

---

### O7 · 2026-11-09 · Own case is not a ceiling of 100%
With X2 = X1 (the scenario's own case, verdict included), base Granite was right 75% of the time in the first 68
self cells of grid B2 (eval v1: 59% main set, 81% held-out). Even with the answer on the card it does not always
follow it. Preliminary (one sample per cell).
- Sources: `results/allpairs/B2/samples.jsonl` (`phase` grid, `x1` == `x2`); eval v1:
  `results/RESULTS-BASE-2026-10-29.md` (arm `self`).

### O6 · 2026-11-09 · No-case accuracy is below chance on the corpus set
First control samples of grid B2: 26% correct (68 samples, one per X1) against a chance level of about 44% (mix of
2-, 3- and 4-option scenarios). Below-chance points to systematic pulls, not noise: off-menu answers (O1), and
possibly the trace's recommendation (deliberately sometimes wrong, design v2.4 §8.2). Preliminary; check again with
all 8 control samples per X1.
- Sources: `results/allpairs/B2/samples.jsonl` (`phase` control), `results/allpairs/B2/report.md` when the run ends.
- To check: control accuracy split by whether the trace's recommended option is gold (`x1` trace record
  `recommended_option`, `data/store/traces/<x1>/trace.yaml`).

### O5 · 2026-11-09 · The leak checker is not consistent run to run
GPT-6 Luna as answer-leak checker (temperature 0) flags some traces on one pass and not the next: 8 traces fixed and
re-checked clean were flagged again on the v3 pass; 6 of 74 B2 scenarios that passed v2 and v3 were flagged on the
v4 pass. Some later flags are real, some are noise ("the chair's docket still has the question in a hold status").
Treating any flag as disqualifying makes the clean set shrink with every pass.
- Sources: `results/allpairs/answer-leak-v2-20261109.jsonl`, `-v3-`, `-v4-`; `results/allpairs/unleak-*.jsonl`;
  review sheet `results/allpairs/LEAK-REVIEW-2026-11-09.md`.
- Idea: majority of 3 checks, or calibrate on Peter's spot check.

### O4 · 2026-11-09 · Jev's option matching is strict about channel and timing
With the v1 option instruction ("the same act, through the same channel or recipient, at the same time"), Jev put
much probability on "none of these" when the base model's option carried routing or extra steps around the same core
choice (e.g. "Approve the warning draft and dispatch it through the authenticated channel now" vs "The War Plans
Division chief sends the draft warning to the Pacific commands": S = 0.44). Match strength is bimodal (580 cells
< 0.1, 288 > 0.8) with a mixed middle band. Fixed by the v2 option instruction (51/53 real matches at 0.5, no false
ones).
- Sources: `results/allpairs/OPTION-JUDGE-TUNING-2026-11-09.md`, `results/allpairs/option-judge-tuning/`.

### O3 · 2026-11-09 · Flip perturbations inherit the parent's decision
In the older (2f) set, several `flip` scenarios still state the parent scenario's decision in a fact or in the trace
(e.g. a flip trace saying the committee "opted against an investigation" while the flipped gold is now different),
so the trace both leaks and contradicts the new gold.
- Sources: `results/allpairs/answer-leak-v2-20261109.jsonl` (entries for `*-flip*@v1`), e.g.
  `DR-ICTY-NATO-1999-flip1@v1`; review sheet `results/allpairs/LEAK-REVIEW-2026-11-09.md`. Risk: R89.

### O2 · 2026-11-09 · Extraction writes the decision into the facts (and sometimes the frame)
The extractor, told that facts are "the record as it stood before the decision", still often wrote the decision
itself as a fact: 39 of 235 older scenarios and 16 of 122 corpus scenarios checked. It can also sit in the frame:
one decider field read "The flight commander, a major, who reportedly authorized the other pilot to attack."
- Sources: `data/store/scenarios/ICTY-NATO-1999/DR-ICTY-NATO-1999-1@v1.yaml` (F7, old text in the
  unleak log), `data/store/scenarios/KUNDUZ-2009/DR-KUNDUZ-2009-3@v1.yaml` (F5),
  `DR-CORPUS-INC-2003-A-10-FRATRICIDE-INVOLVING-THE-BRITI-NS-f8a09055-E1@v1` (decider);
  `results/allpairs/unleak-20261109.jsonl` (`fact_fix.old` / `new`). Risk: R89. Prevention: `extract_fq.v3`,
  leak gate in `pipeline/ingest/corpus_extract.py`.

### O1 · 2026-11-09 · Base Granite lists paperwork steps instead of the decision's options
In some replies the options in `fact_enumeration` are procedural steps taken from the trace's surface (fill in the
register, send the packet, keep a field blank, assemble documents) rather than the decision the answer key frames.
Nothing aligns, so the verdict is off-menu. 50 of 259 B2 samples so far are off-menu (this count also includes
replies with no option list). Interesting for the thesis: if the case helps, part of the help may be in framing the
decision (Q) before any weighing.
- Sources (grid B2, sample id → raw reply under `results/allpairs/B2/`):
  - `base|control|DR-CORPUS-INC-NICARAGUA-COVERT-ACTION-AND-CONTRA-STRAT-NX-2e126ea7-E1@v1|-|0` →
    `raw/base_control_DR-CORPUS-INC-NICARAGUA-COVERT-ACTION-AND-CONTRA-STRAT-NX-2e126ea7-E1_v1_-_0.txt`
    (options about assembling a document packet; the decision is whether to replace the southern-front structure)
  - `base|control|DR-CORPUS-INC-TET-OFFENSIVE-AND-BATTLE-OF-HUE-NS-be8010b5-E17@v1|-|0` →
    `raw/base_control_DR-CORPUS-INC-TET-OFFENSIVE-AND-BATTLE-OF-HUE-NS-be8010b5-E17_v1_-_0.txt`
    (options about finalizing a command-group copy; the decision is whether to continue countryside sweeps)
- Risk: R90. To check: off-menu rate, control vs with-case (`eval.allpairs_report`).
