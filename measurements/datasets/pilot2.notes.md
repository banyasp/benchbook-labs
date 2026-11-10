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
