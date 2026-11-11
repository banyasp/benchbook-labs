# Dataset: pilot2

Generated 2026-11-10T21:40:07Z by `code/eval/analysis/dataset_manifest.py` from `results/transfer/pilot2/cells.json`. Machine-readable manifest: `pilot2.manifest.json` (every file path and a sha256 prefix).

## How this set was selected (provenance)

1. **Pool.**
   - The X1 lists of the all-pairs grids B2, C1 and D1: `results/allpairs/{B2,C1,D1}/x1.txt`, with 64, 93 and 97 ids.
   - All are corpus scenarios that passed the leak checks (v3/v4 plus fixes), are independent decisions, and have live
     traces with no artificial recommendations.
   - The headers of those files give each grid's criteria.
2. **Anchors (40).**
   - Taken from that pool, excluding the pilot-1 anchors (`results/domain-transfer/anchors.json`); each with a live
     trace and at least 3 considerations.
   - Round-robin over domains, random seed 5.
   - Written to `results/domain-transfer/anchors-batch2a.json` and `anchors-batch2b.json` (20 each).
   - This was an ad-hoc query in session 4e83879d; the selection is fully recorded in those two files.
3. **Sister sketches.**
   - Written by a Claude subagent: `results/domain-transfer/SISTER-SCENARIOS-NATSEC-batch2a.md` and `-batch2b.md`.
   - Each anchor got two sisters, A and B, from different national-security sub-domains, with the same considerations
     K. FLAG marks a sister whose setting adds a strong consideration of its own.
4. **Sisters and flips.**
   - Command: `python -m pipeline.transfer --sketch <both sketch files> --log results/transfer/build-batch2-20261109.jsonl`.
   - Written by GPT-6 Luna (role `transfer_writer`).
   - Checked by GPT-6 Luna (role `transfer_checker`) for answer leaks, technique, blind-solve equivalence and added
     strong considerations.
   - Bucketed: accepted (used), hard (`data/store/transfer-hard/`) or rejected (`data/store/transfer-rejected/`).
   - Review sheet: `results/transfer/BATCH2-SISTERS-2026-11-09.md`.
   - Totals: 47 sisters accepted, 25 hard; flips 30 accepted, 38 hard.
5. **Cells.**
   - Command: `python -m eval.transfer_cells --log results/transfer/build-batch2-20261109.jsonl --out results/transfer/pilot2/cells.json`.
   - Every anchor with a live trace and at least one accepted sister gets self, each accepted sister (transfer), each
     accepted flip (flip), and one decoy: the accepted sister of another anchor that shares the fewest equities with
     X1's considerations.
   - Result: 28 X1s. Every run in `measurements/runs.yaml` uses this cell file, or a copy of it in the run directory.
6. **Traces.**
   - render.v5 (GPT-6 Luna renderer, with the answer-leak and framing gates).
   - All 28 last written 2026-11-09 22:24-22:26 UTC (`results/render/rerender-v5b-20261109.jsonl`).
   - The `trace_sha` in the manifest identifies the exact version.
7. **Answer keys are not yet human-reviewed.**
   - All 28 X1 scenarios have `status: needs_review`.
   - Their cases (considerations, weighing, verdict = the answer key) were extracted from source documents by the corpus
     pipeline, an LLM extraction (`code/pipeline/ingest/corpus_extract.py`), and leak-checked.
   - No SME or Peter review yet. Every accuracy number on this set is agreement with an LLM-extracted reading of the
     historical decision.

## Contents

- 28 live scenarios X1 (each with its trace and answer key); cells: self 28, transfer 40, flip 27, decoy 28; plus the no-case arm for every X1.
- Domains: intel-analysis 5, intel-oversight 4, use-of-force-policy 4, operational-command 4, cyber-policy 4, natsec-other 3, gov-ethics 2, military-operational 2.
- Splits: test 13, train 10, dev 5; held out: 7.
- Options per X1: 2 options: 15, 3 options: 13; gold position: 1: 10, 2: 14, 3: 4.

## Where things are

- **Scenario** (facts, question, options, the SME case = considerations, weighing, verdict, flip conditions; the answer key is `case.verdict.choice`): `data/store/scenarios/<family>/<id>.yaml` (schema: `code/bench/schema/pipeline.py` `Scenario`, `code/bench/schema/case.py` `Case`).
- **Trace** (what the agent sees): `data/store/traces/<id>/trace.json` (messages) and `trace.yaml` (span map: where each fact and option is realized). Older versions: `data/store/traces/_versions/`.
- **Served case** for a cell: the X2 scenario's `case`, served as REF1 (the X2 file below).

## X1 scenarios

| # | X1 | domain | split | options | gold | self | transfer | flip | decoy |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `DR-CORPUS-CHILCOT-NX-249d4566-E44@v1` — Civilian Repatriation and Arrival Arrangements | gov-ethics | test | 3 | O3 | 1 | 1 | 1 | 1 |
| 2 | `DR-CORPUS-INC-2016-PRESIDENTIAL-CANDIDATE-INTELLIGENCE-NX-de686566-E2@v1` — Candidate Intelligence Briefing Access | intel-oversight | train | 2 | O2 | 1 | 2 | 2 | 1 |
| 3 | `DR-CORPUS-INC-BATTLE-OF-SAVO-ISLAND-NS-7dd6b155-E33@v1` — Changing an Assigned Patrol During an Emerging Battle | military-operational | test | 3 | O2 | 1 | 1 | 1 | 1 |
| 4 | `DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NX-338578c6-E2@v1` — Assessing Possible Warhead Presence | intel-analysis | test | 2 | O2 | 1 | 2 | 0 | 1 |
| 5 | `DR-CORPUS-INC-CUBAN-MISSILE-CRISIS-NX-3779bf8d-E8@v1` — Choosing a Response to the Cuban Missile Crisis | use-of-force-policy | test | 3 | O2 | 1 | 1 | 1 | 1 |
| 6 | `DR-CORPUS-INC-POLISH-CRISIS-AND-POSSIBLE-MARTIAL-LAW-1-NX-2db78145-E6@v1` — Estimating the Risk of Martial Law | intel-analysis | test | 3 | O1 | 1 | 1 | 0 | 1 |
| 7 | `DR-CORPUS-INC-PUEBLO-CAPTURE-AND-CRYPTOLOGIC-DAMAGE-AS-NS-664e6171-E2@v1` — Response to Compromised January Keying Material | natsec-other | train | 2 | O2 | 1 | 1 | 0 | 1 |
| 8 | `DR-CORPUS-INC-SECRET-SUPPORT-FOR-ITALY-S-CHRISTIAN-DEM-NX-99356abd-E2@v1` — Secret Campaign Funding in Italy | intel-oversight | test | 2 | O2 | 1 | 1 | 1 | 1 |
| 9 | `DR-CORPUS-INC-SOVIET-NONINTERVENTION-DURING-EASTERN-EU-NX-2660676c-E38@v1` — Judging Whether Soviet Strategic Thinking Has Changed | intel-analysis | train | 3 | O2 | 1 | 2 | 2 | 1 |
| 10 | `DR-CORPUS-INC-YUGOSLAV-CRISIS-NS-776ba75b-E1@v1` — Reassigning the Yugoslavia Estimate Draft | intel-analysis | test | 2 | O1 | 1 | 2 | 2 | 1 |
| 11 | `DR-CORPUS-INC-YUGOSLAV-CRISIS-NS-776ba75b-E6@v1` — Whether to Support Active Steps on Yugoslavia | use-of-force-policy | test | 3 | O3 | 1 | 1 | 0 | 1 |
| 12 | `DR-CORPUS-NS-5bdb11ea-E1@v1` — Seeking Direct Leadership Feedback | operational-command | dev | 2 | O1 | 1 | 2 | 2 | 1 |
| 13 | `DR-CORPUS-NS-b39d38e4-E51@v1` — Foreign-Government Gift and Diplomatic Relations | gov-ethics | test | 3 | O1 | 1 | 2 | 1 | 1 |
| 14 | `DR-CORPUS-NS-e1b648f3-E28@v1` — Risk and Deny Flight Enforcement | operational-command | test | 2 | O1 | 1 | 2 | 1 | 1 |
| 15 | `DR-CORPUS-NS-ecc83c1f-E31@v1` — France and the NATO Command Transition | operational-command | train | 2 | O1 | 1 | 2 | 2 | 1 |
| 16 | `DR-CORPUS-NX-1b38b237-E2@v1` — Setting the Kyushu Invasion Date | operational-command | dev | 2 | O1 | 1 | 1 | 1 | 1 |
| 17 | `DR-CORPUS-NX-1eb08268-E7@v1` — Urgency in the Cao-Bac-Lang Campaign | military-operational | test | 2 | O2 | 1 | 1 | 0 | 1 |
| 18 | `DR-CORPUS-NX-2ba79e85-E2@v1` — Disposition of Air America Aircraft and Parts | natsec-other | dev | 2 | O1 | 1 | 1 | 1 | 1 |
| 19 | `DR-CORPUS-NX-3380c2d2-E1@v1` — Irregular Forces and Laotian Neutrality | use-of-force-policy | train | 2 | O2 | 1 | 2 | 2 | 1 |
| 20 | `DR-CORPUS-NX-41af3c89-E2@v1` — The 1973 Second Offset Decision | use-of-force-policy | dev | 2 | O1 | 1 | 2 | 2 | 1 |
| 21 | `DR-CORPUS-NX-476e2d48-E1@v1` — Choosing a Comprehensive Federal Cybersecurity Approach | cyber-policy | dev | 2 | O2 | 1 | 1 | 1 | 1 |
| 22 | `DR-CORPUS-NX-5ced0f03-E4@v1` — MSIC Support During the DIA Transition | cyber-policy | train | 3 | O2 | 1 | 1 | 1 | 1 |
| 23 | `DR-CORPUS-NX-7b45b55b-E3@v1` — Federal SBU Computer-Security Responsibility | cyber-policy | train | 2 | O2 | 1 | 1 | 0 | 1 |
| 24 | `DR-CORPUS-NX-b6a7d193-E2@v1` — Selecting a Network for PANAMAX 18 | cyber-policy | test | 3 | O2 | 1 | 1 | 1 | 1 |
| 25 | `DR-CORPUS-NX-bae93487-E2@v1` — NFIP Funding Oversight | intel-oversight | train | 3 | O3 | 1 | 1 | 1 | 1 |
| 26 | `DR-CORPUS-NX-d0f02cb5-E3@v1` — Identifying Signs at Headquarters | natsec-other | test | 3 | O1 | 1 | 1 | 0 | 1 |
| 27 | `DR-CORPUS-NX-ecd72645-E1@v1` — Reviewing DIA Analyst Resource Allocations | intel-analysis | train | 3 | O3 | 1 | 2 | 1 | 1 |
| 28 | `DR-CORPUS-NX-ecd72645-E3@v1` — Judging Concerns About DIAP Guidance | intel-oversight | train | 3 | O2 | 1 | 2 | 0 | 1 |

## Store-wide context (at generation time)

- Scenario files in `data/store/scenarios/`: 1453 in 829 family folders (all sources, all statuses, sisters and flips included).
- Live traces: 535; rejected renders (`traces/_rejected/`): 197.
- Other pools: `data/store/transfer-hard/` (hard sisters, kept for later), `data/store/transfer-rejected/`.
