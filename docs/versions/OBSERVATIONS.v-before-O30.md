# Observations log

Interesting things noticed while running the pipeline: model behavior, data patterns, judge behavior. Kept next to
`RISK-REGISTER.md`, which records the *risks* (failure modes and what to do about them). An observation that turns
into a risk gets an R-number there and a pointer here. Every entry names its primary sources (sample ids, raw reply
files, scenario files, reports) so it can be re-read. Raw replies and judge matrices live on the box only
(`results/allpairs/<run>/raw/`, `details/`; not in git). Newest first. Started 2026-11-09 at Peter's request.

Paths below are relative to the repo root on the box (`/home/ubuntu/benchbook-labs`).

---

### O29 · 2026-11-14 · Gemma 4 12B copies a flipped case far less than the other small models
On pilot 2's flip-transfer arm, Gemma 4 12B (thinking on, model-card sampling) copies the flipped sister's verdict in
35% (free), 22% (guided) and 29% (schema) of replies and scores 42 / 61 / 55 against the key, where Granite copies
49% / 48% / 49% and scores 28 / 29 / 31, and Olmo copies 69%. Luna copies 10-11% and scores 70 / 77 / 80. Gemma also
keeps its format under the schema (96% readable vs Qwen 48%, Olmo 37%) and thinks longer (median 6.3k-10.0k
characters). A 12B open model gets about halfway from Granite to Luna on the flip, so the flip weakness is not a fixed
property of the size class. Worth reading a sample of Gemma's guided flip replies to see what it does that Granite
does not (it may be the check of whether the flip condition holds in the live trace).
- Sources: runs `results/transfer/pilot2-gemma4-{free,guided,schemaA}` (`samples.jsonl`, `raw/`), M11 size-class table,
  console `/results` (dataset pilot2, metric "Copied the case's verdict").

### O28 · 2026-11-14 · An unrelated case moves no model beyond its own sampling noise (pilot 2)
Scored as Peter asked for the unrelated arm (agreement with the model's own no-case choice on the same X1, not the
answer key), another anchor's case leaves every model where it was. The chance that an unrelated-arm reply matches a
random no-case reply equals the no-case replies' own leave-one-out agreement, within the intervals, for all five
models and three scaffolds: e.g. Granite free 0.86 vs 0.87, Luna schema 0.89 vs 0.89, Qwen guided 0.89 vs 0.89,
Ministral guided 0.63 vs 0.68, Olmo guided 0.61 vs 0.68 (Olmo schema 0.68 vs 1.00 rests on the few readable replies).
So the small models' lower accuracy on the unrelated arm is their no-case accuracy, not distraction. Caveat: the pilot-2
"unrelated" case is a cross-domain sister of another anchor chosen to share few equities, so it is easy to set aside;
pairs-v1's random arm draws any other anchor.
- Sources: `results/tensor/replies.parquet` (rebuilt 2026-11-14 with a `choice` column), console `/results` metrics
  "Agrees with own no-case choice" / "Matches modal no-case choice" (`code/console/results.py`), arms `control` and
  `decoy` of the M11 runs in `measurements/runs.yaml`.

### O27 · 2026-11-13 · Granite read `follows` as "I follow the case's rule"; spelling out the definition fixes much of it
In the gen1 cells where no Granite sample passed, 233 of 324 failed samples had the gold choice and only the relation
label wrong. Granite labelled flips as `follows` because the case's *rule* ("share externally unless an exception
holds") was being followed, though the case's *choice* differed (e.g. PV1-full-00632). With format v4's relation
definitions spelled out against the case's choice ("flips even when you apply the case's own rule"), `flips` rose from
6 to 53 samples on the same cells and 37/81 cells got a passing target. A base-model eval artefact as much as an SFT
one: relation scores of untrained models under v1-v3 understate their grasp of flips.
- Sources: `results/sft/gen1/wv.v2-before-relexp1-merge.jsonl` (rounds of the 81 cells), `results/sft/relexp1/wv.jsonl`;
  prompt diff `code/harness/prompts/versions/format.v4.v0-before-relation-clarified.md` vs `format.v4.md`. M15 addendum.

### O26 · 2026-11-13 · Even with Luna's notes, Granite will not say `flips` on about 1 in 9 flip cells
At scale (M15) the M13 finding persists in a smaller form: with notes that say the relation is flips and name `via`,
Granite still writes `follows` or `distinguished` in 361 of the structure rejections. 86 of 509 cells on flip arms
(transfer_flip, same_domain_flip) had no gate-passing sample in 4 tries and fell back to Luna's text. Base Granite's
prior against "the case's would_change condition fired" is strong. That is what SFT on these arms has to move.
- Sources: `results/sft/gen1/wv.jsonl` (`rounds[*][*].reasons`, `relation`), rows with `source: luna`, e.g.
  PV1-full-02856. Measurement M15.

### O24 · 2026-11-12 · Asked to restate a passage, Granite copies it; given it as notes, Granite rewrites it
In the SFT W experiment (M13), base Granite restating Luna's reasoning passage by passage kept most of the wording
(median per-field similarity 0.83, 12/105 fields verbatim) and the result was no more likely under Granite than Luna's
text. Given the same reasoning as "notes from a senior reviewer" in the prompt and asked to write its own reasoning
after a gold prefill, Granite wrote different text (similarity 0.13) that Granite itself finds far more likely
(+0.66 nats/token), kept the argument (Jev 34/37), and for the first time produced `flips` with `via` (16/18 flip
samples; 0/48 without the notes). Restating also dropped nearly all id citations in 2/21 cells.
- Sources: `results/sft/wexp1/granite.jsonl` (restate, granite_rs), `guided.jsonl`, `likelihood.json`; cells
  PV1-pilot-00330 (verbatim copy), 00282 and 00056 (ids dropped), 00451 and 00148 (guided, read side by side);
  measurement M13.

### O25 · 2026-11-12 · The aligner calls flipped sisters "not governing"
Asked whether X2 governs X1 (on considerations), the Luna aligner said `governs: false` for both transfer_flip cells it
saw in the smoke test, explaining that the case's decisive condition is absent in the live scenario. By the reply
format's definitions that is a `flips` (the case governs and its would_change fires), so the pair gold keeps
governs = true for derived arms and uses the aligner's governs only for the random arm. A model may conflate "the case's
condition fails here" with "the case does not govern" the same way.
- Sources: smoke test of `pipeline.sft.pairgold.align` on PV1-pilot-00002 and the CHURCH transfer_flip cell
  (aligner output printed in the session; the W experiment's stored aligner outputs are in `results/sft/wexp1/write.jsonl`).

### O23 · 2026-11-11 · A self-contradictory prompt cost Luna 2-6 points (M06 vs clean re-run)
M06 (Luna, schema scaffold) appended the v1 mode-C line ("write the YAML documents inside your thinking … then the
verdict as your reply") and the API start line ("begin your reply with `kind: fact_enumeration`"). Luna followed the
second, but accuracy was lower on every arm than in a re-run without the conflict: paired +5 no case, +3 own case,
+2 transferred, +5 flipped, +6 other anchor's case; no-verdict 1-4% → 0%. Lesson: check the assembled prompt for
conflicting instructions whenever a harness option (mode, scaffold, API start line) is combined with another.
- Sources: `results/transfer/pilot2-luna/` (M06), `results/transfer/pilot2-luna-schemaA/`; view
  `measurements/views/SCAFFOLD-ABLATION-luna-v2A-20261111.md`; measurement M11.

### O22 · 2026-11-11 · (CORRECTED) No gold-length cue in anchors; transfer sisters do make the gold longer
First reported as "gold is the longest option in two thirds of corpus scenarios" (66% vs 44% chance). That was a metric
bug: a tie for longest counted as longest, and chance ignored ties. Corrected (characters, unique longest): anchors
39% vs 39% chance, gold/other length 1.00. The cue is real in cross-domain transfer sisters: gold uniquely longest in
40/63 vs 26 by chance, about 15% longer. Flips, rewords and target_f outputs are at chance.
- Sources: `data/store/scenarios/*/` (anchors), `results/ops/ANALYTICS-20261111.md`; measurement M12 (corrected; the
  wrong first version in `measurements/versions/`); risk R6. Fix: `surface_edit` `match_options` after `transfer`.

### O21 · 2026-11-11 · Granite rarely declines an irrelevant case; Luna almost always does (M09, k=8)
On the "other anchor's case" arm (a sister of a different anchor, served as if relevant), Luna declares
`not_governed` in 97% of replies. Granite thinking first declares it in 8%, follows in 47% and distinguishes in 38%;
YAML-only Granite 12% / 37% / 42%. Accuracy on that arm: Luna 70%, Granite 46-48%, about Granite's no-case level. So
Granite is not misled into the irrelevant case's verdict much, but it does not recognise that the case does not apply.
- Sources: `results/transfer/MODE-COMPARE-pilot2-k8-20261111.md` (relations table); `results/transfer/pilot2-modeA/`,
  `results/transfer/pilot2/`, `results/transfer/pilot2-luna/` (decoy phase in `samples.jsonl`); measurement M09.

### O20 · 2026-11-11 · Prompted steps do not fix Granite's flip copying; the YAML schema costs base accuracy (M11)
Scaffold ablation on pilot 2 (28 X1s, all arms). Granite at k=4, think first; Luna at k=8.
- Granite flip arm: 28% (free), 29% (guided), 31% (schema); it copies the flipped sister's verdict about 48% of the
  time under all three. Luna's flip arm gains +7 from guided over free; Granite's gains +1. Telling the small model
  the steps (incl. checking flip conditions) does not make it apply them.
- The YAML schema costs Granite 6-9 points against guided prose on no case, own case and transferred (own case −9
  [−17, −3]); Luna loses 1-3. Free uses about a third of the schema's completion tokens (2,345 vs 7,496 median) and
  never fails to give a verdict.
- The case benefit (+30 transferred − no case) is the same under every scaffold, for both policies.
- Sources: `results/transfer/pilot2-granite-{guided,free}/samples.jsonl`, `results/transfer/pilot2-modeA/` (idx 0-3),
  `results/transfer/pilot2/` (M07); view `measurements/views/SCAFFOLD-ABLATION-granite-20261111.md`; measurement M11.
  Related: O19 (why Granite copies), R92.

### O19 · 2026-11-10 · Why Granite copies a flipped sister's verdict and Luna does not (pilot 2)
Flip cases (`pipeline.transfer` flip.v1) change 1-2 facts so one of the sister's own flip conditions holds, update the
considerations those facts carry (all 30 accepted flips changed at least one consideration's favors or weight; 26
changed the decisive set), rewrite the weighing, and carry one reversed `would_change`. That item is prose in the
SISTER's domain and cites no fact or consideration id (0 of 30); some `if` texts are awkward negations ("Credible new
information did not establish ...").
- Declared relation on the flip arm: Luna flips 52% (always naming the right `via`), distinguished 34%, follows 12%;
  Granite follows 55%, distinguished 33%, flips 1%. Granite mentions a flip condition in its reasoning or
  applicability in 18% of replies (Luna 45%).
- Mapping of the consideration the flip changed: Luna "corresponding" 88% (correct: same equity, different
  direction); Granite corresponding 37%, matched 28% (says it is the same), case_only 21%, absent 14%. Granite's
  case_only lists often name most of the case's considerations and still declare "follows", with no assumption stated.
- Granite does not act on its own mapping: accuracy 26% even when it marks the changed consideration corresponding;
  when it declares "distinguished" it still takes the case's verdict 21 of 55 times (correct 21, off-menu 13).
- Contamination before mapping: share of Granite's OWN live considerations (consideration_enumeration, written before
  any mapping) that favor the flipped case's verdict: control 32%, transfer 19%, flip 45%. Luna: 21%, 18%, 23%.
  Granite rewrites its own view of the situation toward the case's conclusion; Luna does not.
- Not a token budget: Granite's flip replies average about 7,900 completion tokens.
- Open test (queued): Granite in mode A (free thinking, then the YAML) on the same flip and transfer cells:
  `results/transfer/pilot2-modeA/`.
- Update 2026-11-10 (Granite pilot 2 complete, 1,208 samples): no case 45%, own case 81%, transfer 73%, flip 19%
  (copies 57%), decoy 46%. Recomputed on the full run with `code/eval/analysis/mode_compare.py`, contamination is
  control 36% / self 19% / transfer 23% / flip 50% / decoy 31% (Luna 24 / 14 / 18 / 22 / 18). Granite's flip replies
  truncate at 12,000 tokens 8% of the time. Mode A was widened (Peter, 2026-11-10: "allow Granite to think before it
  samples ... apples-to-apples against Luna") to all five arms at k=8 with 20,000 tokens: at 12,000 the free thinking
  truncated 3 of the first 6 flip replies (that 60-sample attempt is kept in
  `results/transfer/versions/pilot2-modeA.v1-12k-tokens-aborted/`). Early sign, not yet a result: mode A thinks far
  longer on flip cells (about 44,000 characters) than on the others (17,000-27,000).
- Sources: `results/transfer/pilot2/` and `results/transfer/pilot2-luna/` (samples.jsonl, raw/), flip cases from
  `results/transfer/build-batch2-20261109.jsonl`; analysis script
  `code/eval/analysis/flip_relation_audit.py` (relation, via and mapping counts; the contamination and cross-tab
  numbers came from ad-hoc queries in the same session).

### O18 · 2026-11-10 · The same cloning again: "What's your call on ..." in v5 final requests
Over the full render.v5 re-render (535 traces), 281 final requests contain "your call" and 199 (37%) open "What's your
call on ...": render.v5 quoted that phrasing as a good example in its lessons section. The line carries no
information about which option is right (every trace has one), so it is a style monoculture, not an answer cue; the
live traces were kept. render.v6 (for future renders) describes the final request without quoting any example.
Second instance of O17's lesson: quoted examples get cloned, including ones labelled "good" or "do not copy".
- Sources: final non-harness message of `data/store/traces/<id>/trace.json` for traces whose `trace.yaml` names
  render.v5; count script in this session (phrase counts above).

### O17 · 2026-11-09 · The renderer clones a single quoted example: stock closing lines
render.v4 gave one example of the final request ("Please give your disposition on the station's reimbursement claim
before the afternoon routing pass."). Of the first 97 v4 traces, 81 ended with "disposition" and 68 began "Please
give…", many with "before the afternoon routing pass" (a 1943 intelligence desk, a ship's bridge). Besides reading
oddly (Peter), a closing line shared across traces is a shortcut cue. render.v5 asks for the speaker's own voice with
several unlike examples marked "do not copy", bans the formula words, and forbids restating the scenario's question
(the first v5 pass produced "What should the FBI do about the proposed preapproval requirement…?" in 6 of 9). The
framing gate adds a deterministic `stock_phrase` check. v5 on pilot 1: "Control, what do you want us doing about the
man still ashore?", "Lieutenant, what's your call on the Article 38 hearing?"; 6 of 10 still contain "what do you
want" (to watch over the full re-render).
- Sources: `results/render/rerender-v4-20261109.jsonl` (v4), `rerender-v5-20261109.jsonl`, `rerender-v5b-20261109.jsonl`;
  traces `data/store/traces/<id>/trace.json` (last non-harness message); v4 versions under
  `data/store/traces/_versions/<id>.pre-render-v5*`.
- Lesson for prompts generally: a single quoted example gets copied; give several unlike ones, or none.

### O16 · 2026-11-09 · Re-rendering with render.v4 lifts GPT-6 Luna's no-case accuracy from 8% to 54%
The 10 transfer-pilot-1 traces were re-rendered with render.v4 (no course in the system prompt, role owns the
decision, the trace ends with a neutral request for the decision, one decision only, no preferences) and the new
framing gate. Luna, same cells: no case 8% → 54% (no YAML verdict 32% → 10%, off-menu 51% → 26%); own case 54% → 84%
(off-menu 25% → 2%). New DR-AUT-001 system prompt gives the agent "latitude to select and execute the vessel's immediate
movement disposition"; the trace ends "Please give your disposition on the extraction movement before the next conning
update." First framing-check version (v1) over-flagged scenario facts that are themselves views (a CO's threat, a
lieutenant's moral view, a memo calling reimbursement an obligation) as "preference"; v2 shows the checker the facts.
- Sources: `results/transfer/pilot1-v4-luna/report.md`, `samples.jsonl`; before: `results/transfer/pilot1-luna/`;
  render log `results/render/rerender-v4-20261109.jsonl`; old traces under `data/store/traces/_versions/<id>.pre-render-v4-*`.
- Granite on the same new traces: `results/transfer/pilot1-v4/report.md` (running at the time of writing).

### O15 · 2026-11-09 · GPT-6 Luna on transfer pilot 1: no-case is just as low, but Luna does not copy flipped cases
Same cells, prompts and scorer as Granite (`eval.allpairs --model luna`; no prefill, an instruction to begin with
the first YAML document instead, plus one sentence saying the YAML is a decision record, not private reasoning, after
Luna refused "private step-by-step reasoning" in the smoke test).
- No case: 8% for both models, for different reasons. Granite names the decision's options and picks a wrong one
  (54% wrong on-menu, 12% right among on-menu). Luna mostly never names them: 32% no YAML verdict (it writes its own
  free-form "disposition"), 51% off-menu (it decides the surface step: verify a routing code, log a discrepancy);
  among the few on-menu replies it is at chance (46%).
- System-prompt authority cue (R93): on the 5 X1s with a non-gold course in the system prompt Luna is 0 right of 40
  (on-menu 0 of 7, and 20 free-form dispositions, e.g. FBI: "Do not adopt… the Bureau retains authority to reject");
  on the other 5 it is 6 of 6 on-menu right. Granite: 0 of 40 vs 6 of 40. Small n (5 X1s each side).
- Flip arm: Luna 40% accuracy and copies the flipped verdict 14% (on-menu accuracy 79%); Granite 6% and copies 62%.
  So the copying is a Granite weakness, not a property of the cells.
- Sources: `results/transfer/pilot1-luna/report.md`, `samples.jsonl`; raw e.g.
  `results/transfer/pilot1-luna/raw/luna_control_DR-CORPUS-NS-7d5e5ea6-E6_v1_-_0.txt` (free-form disposition citing
  the authority), `raw/luna_control_DR-CORPUS-NX-09fb3b9c-E2_v1_-_0.txt` (decides the routing-code step);
  Granite side `results/transfer/pilot1/report.md`.

### O14 · 2026-11-09 · Transfer pilot 1: no-case accuracy 9% comes from consistent trace cues, not the scorer
Pilot 1 control (no case): 6 of 72 correct; chance is about 42% (five 2-option, five 3-option X1s). Breakdown of
the 72: 4 no verdict parsed (format), 14 off-menu because the reply framed a different, paperwork-level decision
(O1), 8 off-menu with a borderline option match (S 0.1-0.5; some look right, e.g. "set out a separate B5
conclusion" vs gold "rejects the British assessment and transmits its own conclusions", S 0.29-0.45), 40 on-menu
wrong, 6 on-menu right. The model is nearly deterministic per X1 (often 7 of 7 the same option), so the effective n is
10 scenarios, and it gets about 1 right. The pulls toward the wrong option:
- The renderer's `system_scope` channel (render.v3 rule 2) states a standing authority for one course in the system
  prompt, and the model reads the permission as the rule. In 5 of the 10 X1s that course is not gold; control there is
  0 of 38, and the replies cite it as decisive ("The strongest constraint comes from the Bureau's standing authority
  to reject…"). Store-wide, 319 of 589 live traces put an option in the system prompt, 218 of them a non-gold one.
  In B2 the same split moves control far less (gold 46%, none 36%, non-gold 39%; 180 samples), so the cue does not
  always bite.
- DR-AUT-001 still carries an artificial recommendation for the wrong option ("I'd lean toward the hold", message
  8): the no-recommendation re-render covered the corpus pools only. 109 of 589 live traces still carry one.
- Base Granite sometimes writes the whole four-document reply twice; the parser reads the first copy.
- Sources: `results/transfer/pilot1/samples.jsonl` (phase control); raw replies
  `results/transfer/pilot1/raw/base_control_DR-CORPUS-NS-7d5e5ea6-E6_v1_-_0.txt` (cites the authority),
  `raw/base_control_DR-AUT-001_v1_-_1.txt` (follows the recommendation, never lists the C2 module),
  `raw/base_control_DR-CORPUS-NX-1fb1e4ff-E3_v1_-_2.txt` (borderline match); traces
  `data/store/traces/DR-CORPUS-CHILCOT-NX-249d4566-E59@v1/trace.json` (message 0: "HRD's standing delegation
  permits it to waive medical confirmation…"; the model waives).
- Risk: R93 (and R91 for the leftover recommendations).

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
