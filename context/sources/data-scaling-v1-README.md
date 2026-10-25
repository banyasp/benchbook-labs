# Real data for the Benchbook — research and pilot (v1, 2026-09-29)

Readable version (Claude Doc): "Real Data for the Benchbook: Sources and Procedures"
https://claude.ai/code/artifact/5da7daa2-9cb0-46c8-8dd3-873044628f5c (tab 2 = full source catalog)

| Path | What it is |
| --- | --- |
| research/A-alignment-agentic.md | Alignment, value and agentic-safety datasets and environments (2022–2026), mapping table |
| research/B-natsec-evals-and-case-libraries.md | Natsec AI evals, LLM wargames, professional ethics case libraries, mapping table |
| research/C-adjudicated-decisions.md | DOHA/DOE clearance decisions, FISC/702, Five Eyes oversight bodies, whistleblower and military-justice corpora, mapping table |
| research/D-authentic-noise-corpora.md | Declassified records, investigations with transcripts, captured-document releases, workplace corpora, exclusions |
| research/E-methods-anticollapse.md | Collapse/homogenization evidence, diversity methods, leakage tests, thresholds, pipelines P1–P5, budget |
| source-catalog.csv | All 150 assessed sources with fit ratings (exemplar / live / held-out) |
| pilot/ (and pilot-v1-2026-09-29.zip) | The DOHA Guideline F pilot: SEAD 4 catalog (catalog-F.yaml), 10 converted real decisions (cases/), 3 FISC 702 query cases, run_heldout.py + heldout-results.md (run on your unmodified solver_v2.py), live-scenario/ (15-item re-situated case file + salience.yaml; synthetic), tools/ (classify, validate, anchor and salience checkers), PILOT-NOTES.md |

Not copied: pilot/raw/ (134 MB of public DOHA PDFs and SEAD 4 scans used for provenance). Every case cites its decision URL.

Hygiene: official public releases only; no leaked material. The live scenario invents all people, companies and accounts. DOHA blocks automated clients — get permission or bulk access before fetching at scale; DOE listings allow ordinary requests.
