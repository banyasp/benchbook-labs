# pipeline.ingest (2f P1): registry, acquire, normalize, extract, import-pilot

Run with `PYTHONPATH=code /home/ubuntu/benchbook-labs/.venv/bin/python -m pipeline.ingest <cmd>`.

| cmd | does | writes |
|---|---|---|
| `registry` | validates `sources.seed.yaml` against `context/sources/source-catalog.csv`, computes per-family splits | `data/store/registry/sources.yaml` |
| `acquire` | polite fetch (descriptive User-Agent, 1.5 s apart) of each source URL; never rewrites an existing raw file | `data/raw/<sha256>` + `.meta.json`, `registry/acquired.yaml` |
| `normalize` | raw -> paragraphs with stable span ids; re-run is byte-identical (a changed file would be versioned) | `data/docs/<sha12>.jsonl` |
| `extract [--source ID] [--episode N]` | two model calls per scenario (see below), schema + grounding gate, up to 3 attempts per call | `data/store/scenarios/<family>/<id>.yaml` (+ `extract-logs/`) |
| `import-pilot` | copies the 10 converted pilot cases as eval-only scenarios | `data/store/scenarios/<family>/` |
| `status` | counts, splits, grounded facts | - |

## PDF text
The main venv has no PDF library (and must not be modified). `normalize` runs `pdf_text.py` (pypdf 5.4.0) as a subprocess
with the interpreter in `BENCHBOOK_PDF_PYTHON`. Tonight that is a separate venv in the session scratchpad:
`uv venv <dir>; uv pip install --python <dir>/bin/python pypdf==5.4.0`, then
`export BENCHBOOK_PDF_PYTHON=<dir>/bin/python`. Paragraphs = blank-line-separated blocks of a page (pypdf keeps the PDF's
paragraph gaps), page-number lines dropped, wrapped lines joined. Span id = `src:<sha12>#p<page>.<para>`; XML/HTML are one page.

## extract
1. `prompts/extract_fq.v1.md`: facts (each with span ids), question frame, 2-4 options as a matched set (checker: longest <= 1.3x
   shortest in words), `real_option`. Code then shuffles option order (seeded by scenario id) so the real outcome's position is not a cue.
2. `prompts/extract_a.v1.md`: given F, Q and the spans: considerations (equities from `data/registry/equities/pilot.yaml`), reasoning,
   verdict (must be the real option; `basis_statement` = the source's words), flip conditions with `origin: stated|authored`.
Validation: JSON -> 2a `Case` model (all cross-references) -> gates (equity ids, verdict = real option, `stated` flips cite spans, >= 1
would_change). Errors go back to the model (max 3 attempts). Gate: schema-valid and every fact has a span ref or is in `provenance.authored`.
Everything the model invented is in `provenance.authored` (non-real options, authored flip conditions, facts without spans, synthesis fields).
Tags: `options-authored`, `agent-recast`, `flip-conditions-authored`, `cue:option-length`, `gold-move:<ask|hold|refuse>`.
Cues are also stored in `case.library.cues`.

## Splits
Per family (one family per document, or per vignette for the regulation), assigned at extract time: families sorted by
sha256(family id); first -> test, second -> dev, the rest train. Recorded in `sources.yaml` (`split_rule`, `splits`).

## Rules kept
Bedrock only through `bench.models.complete('extractor', ...)`; no GPU; `data/cases/` and `data/scenarios/` are never written.
