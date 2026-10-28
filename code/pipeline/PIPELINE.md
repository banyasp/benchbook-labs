# Data pipeline — operator contract (2f 2026-10-25; v2.4.1 rebuild in progress 2026-10-28)

> **v2.4.1 (BUILD-BRIEF-v2.4-2026-10-27, design `context/DATA-PIPELINE-DESIGN-v2.md` v2.4.1) supersedes the 2f
> rows below where they differ:** the SFT writer is **rejection sampling Granite (no gold, mode C)**, the gold-informed
> teacher is kept only as `--writer teacher`; pairs carry `arm` / `card_view` (ids hash both); traces live once per
> trace scenario in `data/store/traces/<id>/` (TraceRecord: σ with option spans, channels, recommended_option);
> options are plain text discoverable in the trace (never tools, never a menu); served cards strip
> `move` / `irreversible` / `to:`; splits = per source document, ~20/10/70 per domain, the held-out domain
> (military-operational) all test. The 2f text below is kept as the record of the first build. 2f version:
> `versions/PIPELINE.v1-2f-teacher.md`.

Work order: `BUILD-BRIEF-2f-2026-10-25.md` (wins over older files). Design: `context/DATA-PIPELINE-DESIGN-v2.md`
§2-4b, §6. Risks: `docs/RISK-REGISTER.md` (append new ones). Records: `code/bench/schema/pipeline.py`
(`Scenario`, `PairRecord`, `Provenance`, `SpanMap`, `GoldMap`, `Touched`); store: `code/pipeline/store.py`.
Models only through `bench.models.complete(<role>, messages)`: roles `extractor`, `perturber`,
`independent_solver`, `renderer`, `teacher` (config/models.yaml; placeholder gpt-oss-120b on Bedrock). Never the
policy/base model. Run with `PYTHONPATH=code /home/ubuntu/benchbook-labs/.venv/bin/python`.

| Package (owner) | Operator | Signature | Gold produced |
|---|---|---|---|
| `pipeline/ingest/` (P1) | registry, acquire, normalize | catalog → `data/store/registry/sources.yaml`; URL → `data/raw/<sha256>` + `.meta.json`; raw → `data/docs/<sha12>.jsonl` (span ids `src:<sha12>#p<page>.<para>`) | — |
| `pipeline/ingest/` (P1) | extract | doc spans → `Scenario` (F, Q first with span refs; then A from the endorsed answer; `basis`; matched option set; family + split) | `source-endorsed` (or `model-solved` if the source endorses none) |
| `pipeline/ingest/` (P1) | import_pilot | 10 converted pilot cases (`data/cases/`) → eval-only `Scenario`s (copy; don't touch `data/cases/`) | as recorded by 2b |
| `pipeline/perturb/` (P2) | restyle, flip, add_fact | `Scenario` X → (`Scenario` X′, partial `PairRecord` with gold M_{C,T}, relation, via, choice, gold_tier, touched) | restyle/flip `by-construction`; add_fact `model-solved` by `independent_solver` that never sees X |
| `pipeline/pair/` (P2) | pair | store → `PairRecord`s: derived (C=X, T=X′) + decoys (unrelated C, `not_governed`); caps hand-up golds ≤ 1/3 per arm, balances gold option positions | relation by construction |
| `pipeline/render/` (P3) | render | T `Scenario` (+ raw doc for texture) → `trace.json` (TRACE-FORMAT v2.6, ends at the decision point with the `{{CARD}}` injection) + `SpanMap` | — |
| `pipeline/solve/` (P3) | solve (teacher) | (trace, equities, served C, **full gold structure**, touched condition, structure-mapping rubric) → N=3 replies in the PDF `kind:` format; accept iff parses and matches gold verdict, relation, via and mapping buckets | process text only (never gold) |
| `pipeline/project/` (P3) | project | `PairRecord` → SFT jsonl (prompt messages + target; loss on target only), RLVR json (record minus reasoning prose and applicability-why; keeps governs/relation/via), Inspect samples + 2a `AnswerKey`; must load in `code/training/sft_data.py` and `code/scorers` | — |

Rules (brief): gold verdicts only from construction → source-endorsed → independent solve that never sees C;
provenance on every artifact (`Provenance.steps` + `fields` + `authored`); keep every version; safety scope =
decision ethics, law and policy only; build nothing on the deferred list (§10 of the design).
