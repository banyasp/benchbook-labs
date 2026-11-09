# Observations log

Interesting things noticed while running the pipeline: model behavior, data patterns, judge behavior. Kept next to
`RISK-REGISTER.md`, which records the *risks* (failure modes and what to do about them). An observation that turns
into a risk gets an R-number there and a pointer here. Every entry names its primary sources (sample ids, raw reply
files, scenario files, reports) so it can be re-read. Raw replies and judge matrices live on the box only
(`results/allpairs/<run>/raw/`, `details/`; not in git). Newest first. Started 2026-11-09 at Peter's request.

Paths below are relative to the repo root on the box (`/home/ubuntu/benchbook-labs`).

---

### O13 · 2026-11-09 · Sketching sisters surfaces anchor defects
Writing sisters forces a close read of the anchor's K, and the sketch subagents found problems the leak checks
passed: DR-CORPUS-NX-e5bfbd43-E6@v1 F5 states the decider's own assessed preference (the decider is the Kremlin);
DR-CORPUS-NX-1eb08268-E7@v1 has the governing directive signed by the decider's own commander;
DR-CORPUS-NSARCHIVE-BOP-NX-1c6c919b-E1@v1's verdict rests on two weak considerations against two strong ones, with a
strong consideration for the opposite option marked decisive (K and verdict inconsistent); several anchors' `why`
texts carry hindsight or the verdict (e.g. a subcommittee's belief called "apparently mistaken"; an Act Congress
later passed). The `why` texts are part of A (shown on cards, never in traces), but the first three affect X1 use.
- Sources: `results/domain-transfer/SISTER-SCENARIOS-NATSEC-batch2a.md` and `-batch2b.md` (overviews and fidelity
  lines); the scenario files under `data/store/scenarios/CORPUS-*/`. To do: re-check these anchors; consider a
  K-consistency check (decisive considerations must favor the verdict).

### O11 · 2026-11-09 · "Ask / defer" options are almost never the answer (shortcut cue)
Across the 397 live corpus scenarios, options by move and how often each is gold: act 388 of 820 (47%), hold 5 of
45 (11%), ask 2 of 58 (3%), partial 2 of 14 (14%). A model that never picks "ask someone first" is right almost
every time it skips one. Spotted by the domain-transfer subagent (six of its 18 anchors have a never-endorsed defer
option), confirmed by count. This is R58 (the source's real answer is nearly always an `act`), measured on the
corpus. Matters for perturbations: a sister generator that strengthens the defer option changes K.
- Sources: scenario files `data/store/scenarios/CORPUS-*/` (`case.options.*.move`, `case.verdict.choice`);
  `results/domain-transfer/SISTER-SCENARIOS-2026-11-09.md` (overview). Risk: R58.

### O12 · 2026-11-09 · Domain transfer: what transfers and what drifts
A strong-model sketch of 39 sister scenarios for 18 anchors: structural considerations (a bar on self-created
urgency, a necessity threshold plus warning, one person vs. many exposed, first-party evidence vs. outside
skepticism) transfer cleanly; considerations that rest on who endorsed what, or on a legal doctrine specific to the
source, resist. The commonest drift is the new domain ADDING a strong consideration of its own (patient safety,
disclosure law), sometimes a hard legal bar. Some `why` texts restate the verdict, so they must never be copied into
a sister's facts.
- Sources: `results/domain-transfer/SISTER-SCENARIOS-2026-11-09.md`, `results/domain-transfer/anchors.json`.

### O10 · 2026-11-09 · What the trace recommendations look like
206 of 416 live corpus traces carry a recommendation (design default 50%, `RECOMMEND_SHARE` in
`code/pipeline/pair/channels.py`; option picked at random; 78 point at gold). A read-through of all 206 (Haiku
subagent, spot-verified): almost all are a staff member's soft personal view ("I'd keep...; it keeps the record
practical"), never an order (2 of 206 contain "must/please/you should"; about 60% start with an explicit hedge such as
"I'd" / "I would"). Speakers: peers, desks and liaisons (~100), operators/leads (~60, "ops-lead" alone 17), document
margin notes and log entries (~80). Five channels roughly evenly (system scope 50, tool result 47, operator 38,
colleague 36, attached document 35). Most sit early-to-middle in the trace, with a second cluster just before the
decision. Status-quo advice dominates (~half use keep / leave / retain / hold). About 1 in 5 read as inserted (an
advisor with no reason to advise, generic rationale). About 10 are effectively the decision itself (a pre-filled
disposition the agent is asked to sign or file, e.g. "I'd sign it"). Some restate the recommended option's wording
almost verbatim. One recorded span holds no recommendation at all.
- Sources: `results/allpairs/RECOMMENDATIONS-2026-11-09.md` (all 206 with context and trace paths),
  `results/allpairs/recommendations/recs.json`; examples DR-CORPUS-NX-25c7082f-E4@v1 ("I'd sign it"),
  DR-CORPUS-NX-026edc60-E6@v1 (restates the option), DR-CORPUS-NX-940aa988-E1@v1 (span without a recommendation).
  Related: O8, R91.

### O9 · 2026-11-09 · With a case, some replies never commit to a verdict
In grid B2 (interim, 1,547 with-case cells), 10% of with-case replies have no verdict choice against 3% without a
case; truncation explains little (4%). In 90 replies the verdict document is just `kind: verdict` followed by "...",
after which the model argues with the format instructions ("close your thinking with </think> ... then write the
verdict document as your reply"?) and never writes a choice. Another ~20 stop after `applicability` or `reasoning`.
The with-case format (more steps, the think/verdict split) seems to confuse the base model; scored as wrong.
- Sources: `results/allpairs/B2/samples.jsonl` (`phase` grid, `parsed_choice` null), e.g. raw replies of
  `base|grid|DR-CORPUS-INC-NICARAGUA-COVERT-ACTION-AND-CONTRA-STRAT-NX-2e126ea7-E1@v1|…` and
  `base|grid|DR-CORPUS-INC-YUGOSLAV-CRISIS-NS-776ba75b-E1@v1|…` under `results/allpairs/B2/raw/`; prompt text
  `code/harness/prompts/format.v1.md`. Related risk: R87.

### O8 · 2026-11-09 · The base model follows the trace's recommendation
Traces contain a message urging one option (design v2.4 §8.2; deliberately sometimes wrong). In grid B2 (interim),
no-case accuracy is 60% when the trace recommends the gold option (5 X1s), 14% when it recommends another option
(24 X1s) and 38% with no recommendation (39 X1s); with a random case 53% / 13% / 32%. Even with its OWN case (verdict
on the card) the model is right only 62% of the time when the trace recommends a different option, against 100% /
79% otherwise. This explains O6 (below-chance control). In the clean corpus pool, recommendations point at gold in
78 traces, elsewhere in 128, and 210 have none.
- Sources: `results/allpairs/B2/report.md` ("By the trace's recommendation"), `results/allpairs/B2/samples.jsonl`,
  `data/store/traces/<x1>/trace.yaml` (`recommended_option`), `pipeline/render/channels.py` (pick_recommended).
- Why it matters: the case's job here is partly to overrule a wrong recommendation; the B2 headline mixes three
  very different regimes. Risk: R91.

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
