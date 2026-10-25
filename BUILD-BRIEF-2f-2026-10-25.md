# Build brief — 2f data pipeline, critical path (2026-10-25, tonight)

*The work order for the EC2 session. Written in Peter's claude.ai session from everything decided today.
Read first: `CLAUDE.md` → `DECISIONS-2026-10-25.md` → `context/DATA-PIPELINE-DESIGN-v2.md` (v2.2; §1–4b, §10)
→ `docs/RISK-REGISTER.md`. Where this brief and older files differ, this brief wins. 2f is no longer on hold:
build the critical path below, nothing more.*

## Goal and definition of done
One thin, working path from public sources to SFT / RLVR / eval records, end to end, tonight.
**Done when** ≥ 20 (C, T) pairs flow through every operator, the SFT records load in `code/training`'s SFT
builder, the RLVR records load in `code/scorers`, and `results/DATAGEN-2026-10-25.md` lists 3 example pairs for
Peter to read. Checkpoint 2 keeps priority on the GPU; this work uses CPU + Bedrock + OpenRouter only.

## Concepts (design v2.2 §2–3)
- **Scenario X = (F, Q, A)** — role-agnostic: facts; question frame (question, decider, agent role/authority,
  options with move type and irreversibility); answer (considerations, reasoning, verdict, flip conditions, lesson,
  limits). It is the PDF case format plus lineage, provenance and status. Reuse the 2a models
  (`code/bench/schema`); extend, don't fork.
- **Roles:** served as a case C (card) or rendered as a trace T. Any scenario can be either.
- **Data operators:** `extract`, `perturb`, `pair`, `render`, `solve`, `project` (signatures in design §3).
- **Gold verdict for T, strictly in this order:** by construction → the source's endorsed answer → an independent
  solve that **never sees C**. The dependent `solve` is never a gold source.
- **Every perturb operator emits the gold mapping** M_{C,T} and the weighing condition it touched (design §4).

## Storage (new; don't disturb Checkpoint 2's data)
- `data/raw/<sha256>` + `.meta.json` (immutable), `data/docs/<sha12>.jsonl` (span ids
  `src:<sha12>#p<page>.<para>[a:b]`), `data/store/scenarios/<family>/<id>.yaml`, `data/store/pairs/<pair-id>/`
  (pair record, trace, span map), `data/exports/<version>/{sft,rl,eval}/`.
- Leave `data/cases/` and `data/scenarios/` (2b's layout, used by Checkpoint 2) untouched. Import the 10 converted
  pilot cases into the new store as eval-only scenarios. Note the eventual migration in the register.

## The critical path
1. **Registry + acquire + normalize.** Default sources (Peter may override): **3 DOHA security-clearance Appeal
   Board decisions** (written reasoning, an endorsed outcome) and **1 doctrine or training-scenario source** from
   `context/sources/source-catalog.csv` or the Hard Calls research strands in `context/seeds/hard-calls-v1/`.
   Fetch from this box; if a site blocks fetching, say so and use another public source rather than working
   around the block. Public material only.
2. **extract** (Bedrock `openai.gpt-oss-120b-1:0`): F and Q first (facts cite span ids), then A from the source's
   endorsed answer and stated reasons; record `basis`; flip conditions only where the source states them, else
   tagged `authored`. Recast the decider as an agent only where the decision's structure carries over (tag it).
   Options as a **matched set** (all rewritten to similar length and specificity, real option included).
   Assign family id and split (train / dev / test) per family now. Gate: schema-valid; span refs present.
   Target 6–10 scenarios.
3. **perturb** — three operators, each emitting X′, its answer, the gold M_{C,T} and the touched condition:
   `restyle` (follows); `flip` realized **indirectly** (never a paraphrase of the `would_change` item — design
   §4a); `add fact` (an unlisted fact; X′'s verdict by an **independent solve** with gpt-oss-120b at high reasoning
   effort that does not see the case; tag `model-solved`).
4. **pair:** derived pairs (C, T = perturb(C)) plus decoys (unrelated scenarios, `not_governed`). Cap hand-up golds
   at ≤ 1/3 per arm; balance gold option positions (R6, R7).
5. **render** (gpt-oss-120b): the trace in `examples-v21/templates/TRACE-FORMAT.md` form, ending at the decision
   point, plus a **span map** (for each fact: message index, character range, realization stated / paraphrased /
   implied / split) and the allowed list of true-but-unneeded details. Spread facts across channels; no verbatim
   copying. Emit the span map now; its gates come later.
6. **solve** — the **teacher** writes the full reply in the PDF step format (`kind:` documents, `via` in the
   verdict), given the trace, equities, served case **and the full gold structure** (mappings, applicability,
   relation, `via`, verdict, touched condition) plus the structure-mapping rubric (design §4b: map the case's
   conditions and relations, not surface facts). **Never the base model.** Teacher = config setting; tonight's
   placeholder is gpt-oss-120b at high effort. N = 3 samples per pair; keep a sample only if it parses and matches
   gold on verdict, relation, `via` and the mapping buckets. **Log acceptance rates** per pair type (R27).
7. **project** (code only): SFT records (prompt messages; target; loss on the target only — trace, equities and
   case masked), RLVR records (the gold pair record without reasoning prose or applicability-why; keeps `governs`,
   relation, `via`), Inspect samples. Must load in `code/training` and `code/scorers`.

## Rules
- **Provenance on every field and artifact:** model id, prompt version, input hashes, operator, gold tier
  (`by-construction` / `source-endorsed` / `model-solved`). The open-weight authorship allowlist is lifted: change
  `code/datagen/models.yaml` (and `llm.py` if needed) to **record** provenance, not refuse.
- Judge calls, if any, go to Jev via OpenRouter through the existing cached interface.
- Safety scope: decision ethics, law and policy only; no weapons employment, targeting, intrusion, collection or
  covert-communication technique.
- Keep every version of prompts, schemas and outputs (`versions/`). Commit and push often.
- Delegate grunt work to subagents (Sonnet), as before; one directory each.
- Bedrock spend: soft cap $100 tonight; report actual spend.
- When you hit a new risk, shortcut cue or data artifact, append it to `docs/RISK-REGISTER.md`.

## Deferred — do not build tonight (design §10)
Grounding judge, A/B render test, salience probe, verbatim check, option-specificity gate, two-solver agreement,
thin cards, twin-contrast filter, Horty a-fortiori checker, legal-opinion corpus, natural-pair matching and the
structural index, transfer operator, review UI, judge validation set, oracle-consistency audit.

## Report (`results/DATAGEN-2026-10-25.md`)
Counts per stage; acceptance and rejection reasons per gate; teacher acceptance rate per pair type; gold-tier mix;
hand-up and option-position balance; Bedrock spend; time per stage; 3 example pairs (paths) for Peter; new risks
logged.

## Still open with Peter (don't block)
Source picks beyond the defaults; the teacher model; teacher-only vs teacher-then-base-rewrite (self-distillation);
legal opinions as a training domain; distance weights; the reward function; `partner_relationship`;
`decisive_in_case`.
