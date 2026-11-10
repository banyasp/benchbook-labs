# M10 · Earlier and stopped measurement sets (pointers)

This file lists measurement sets from before 2026-11-09, or ones stopped before completion, so the record is complete.
Their numbers are in their own reports and are not repeated here. They should be brought into M-entries as they are
re-used.

| Set | Status | Data / report | Note |
|---|---|---|---|
| All-pairs grid B2 (Granite, 64 × 64 X1/X2) | STOPPED, SUPERSEDED (1,511 samples) | `results/allpairs/B2/` (`config.json`, `samples.jsonl`) | Started 2026-11-09 02:15 UTC on render.v3 traces (before the framing fixes, M02/M04) and stopped; Peter to decide whether to restart on the new traces. Its control split by system-prompt option (gold 46%, none 36%, non-gold 39%; 180 samples) is quoted in M02 |
| All-pairs B1 (120 samples), A1, smoke, smoke2 | small / smoke | `results/allpairs/{B1,A1,smoke,smoke2}/` | Harness checks |
| Answer-leak review, recommendation audit, option-judge tuning | COMPLETE | `results/allpairs/LEAK-REVIEW-2026-11-09.md`, `RECOMMENDATIONS-2026-11-09.md`, `OPTION-JUDGE-TUNING-2026-11-09.md` | Leak checker and option judge are LLM judges (GPT-6 Luna; Jev) |
| Base and SFT-1 results, datagen, H3 pilot, equity mapping | COMPLETE (Oct 2026) | `results/RESULTS-2026-10-25.md`, `RESULTS-BASE-2026-10-29.md`, `RESULTS-SFT1-2026-10-29.md`, `SFT1-2026-10-29.md`, `H3-PILOT-2026-10-28.md`, `EQUITY-MAPPING-2026-10-28.md`, `DATAGEN-*.md` | Earlier pipeline (Checkpoint 2 era); see each report for its method |
| Costs | as of 2026-10-28 | `results/COSTS.md`, `results/costs.json` | Not regenerated for the November runs |
