# Benchbook Labs — standing context for Claude

*Written 2026-10-25 from Peter's claude.ai project ("Recruiting and Learning") so a Claude Code session on the
EC2 box starts with the same context. Today's sprint plan is in `HANDOFF-2026-10-25.md`; read it next.*

## The project in one paragraph

**The Benchbook: Alignment at the Edge** (Peter Banyas). A harness monitor watches an agent; when the agent nears
a consequential decision, the harness pauses it and injects a short list of the deployer's *equities* plus a
*reference case* (an SME's worked decision: facts, considerations, weighing, verdict, flip conditions). The agent
reasons from the case by analogy and then acts through tool calls. **Thesis:** LLMs that are both (1) trained to
reason analogically and (2) served relevant exemplar cases at inference time make more aligned choices out of
distribution than either alone. Selling points: pluralism (each deployer steers with its own tradecraft), privacy
(cases never enter a lab's training data), online edits (change the library, behavior changes now),
generalizability (cases transfer across domains with the same structure), explainability (the trace cites
precedent). Policy model: an ~8B open-weight instruct model with tool calling, one LoRA adapter.
Full plan: `context/Benchbook-Research-Plan-v0.4.pdf`.

## How Peter works (follow these)

- **Think with him.** He welcomes questions at the start and mid-work. Ask when a decision is his (see the open
  decisions in the handoff); don't silently pick. Recommend an option when you have a view.
- **Keep every version.** Never overwrite a draft, spec, prompt or result: copy the old one into a `versions/`
  folder next to it (name it `<file>.vN-<what changed>.<ext>`) before editing. This repo already follows that.
- **His own writing is authoritative.** Documents Peter wrote beat AI-generated derivatives. Everything under
  `context/` and most of `ideas/` was drafted *with* Claude in earlier sessions; treat it as strong context, not
  law, and flag contradictions instead of resolving them yourself.
- **The schema is authoritative over datagen.** `examples-v21/templates/` (reference v2.3, live v2.5, mapping
  v2.5, TRACE-FORMAT v2.6, DATAGEN-SPEC) is the formal spec. The datagen pipeline must change to fit the schema,
  never the reverse. (The *reply* format has since moved on; see "Known drift" below.)
- **Flag shortcut cues** whenever you see them: option order or position, answer length, the gold always being
  "escalate"/hand-up, number of supporting facts. Models must not learn those instead of the reasoning.
- **His time is the scarce resource.** At most ~5 hours of his own time for data auditing/curation/writing in
  total. Spend LLM compute instead. He has OpenRouter and OpenAI credits, AWS Bedrock, and Claude Max.
- **Edit files in place in this repo**; no zips.
- **Implementation over more design.** As of 2026-10-25 he has spent weeks designing and writing. The goal now is
  running experiments and real numbers, fast (results within 1-2 days for a possible OpenAI research
  presentation this week; ACL surgery on Nov 20).
- **Safety and sourcing (from the drafting briefs).** Cases stay at the level of decision ethics, law and policy.
  No weapons employment, targeting, intrusion, collection or covert-communication technique; "tradecraft" means
  decision practice only. Invented facts are fine and flagged in `provenance.caveats`. Keep `[UNVERIFIED]` marks.

## Peter's standing design decisions

- The harness injects the case; the agent never fetches it with a tool call.
- Default agent stance is true long-horizon autonomy: it figures out what to do and does it. Always escalating to
  a human is a crutch. "Escalate when no close case exists" may be an optional deployer setting, never the default.
- Scenarios are deliberately simple in form; judgment, values and tradecraft live in prose, not in an if-tree.
- **Agent pipeline (Oct 2026):** after injection the agent writes, in order: case-fact discretization of the live
  trace → fact mapping (matched / altered / live-only / case-only) → consideration enumeration → consideration
  mapping (carried / revised / live-only / case-only; copy where facts match, rework where altered, reason de
  novo for new facts, state assumptions for absent ones) → applicability (`governs`) → reasoning → verdict → tool
  calls. Worked example: `context/schema/benchbook-analogical-pipeline-example-v7.yaml`. Extracting facts before
  seeing cases is future work.
- Relations: `follows | flips | distinguished | not_governed`. **`not_governed` ends the agent's reasoning, and
  nothing it does after deciding not_governed is rewarded or punished** (he is not training judgment independent
  of the case). Governance is decided on considerations, not fact overlap.
- **No numeric `confidence` in the verdict** (dropped Oct 2026), so the reward has no calibration term.
- The decision *is* the tool calls, matched to a live option by a hidden signature (`calls` / `without`). Options
  are never listed to the agent.
- Training: LoRA SFT (label-conditioned, STaR-style targets generated by the base model and filtered by the
  scorer), then GRPO (Dr. GRPO normalization, 8 rollouts, KL to SFT) with a deterministic scorer. Prose is never
  scored by RL. Prefer one scorer package shared by TRL (training) and Inspect (eval).
- **Eval infrastructure: UK AISI Inspect (`inspect_ai`).**
- **Headline experiment:** alignment (action) accuracy vs. distance from the live scenario to the nearest
  reference case, one curve per arm (base / harness / SFT / SFT+RL), showing alignment generalizes and the arms
  are additive. Distance is computed structured-YAML to structured-YAML, never against traces. Second graph:
  accuracy vs. library size per arm ("scaling law for alignment"). Core generalization first; library-improvement
  work later.
- Cross-domain transfer (structurally similar case from another domain) is the big value-add of analogy; one whole
  domain is held out for the test.
- Data authorship rule (DATAGEN-SPEC §10, `code/datagen/models.yaml`): **training-bound** text and labels come only
  from allowlisted open-weight families (gpt-oss, gemma-4, mistral, olmo), real documents, or Peter. Claude and
  closed GPT models may review, prototype and write **eval-only** material. Batch B001 is Claude-drafted, so it is
  eval-only.

## Where things are

| Path | What |
|---|---|
| `examples-v21/templates/` | **The formal spec** (templates, `DATAGEN-SPEC.md`, `TRACE-FORMAT.md`, `TRAINING-HANDOFF.md`) |
| `examples-v21/<CASE>/` | 13 worked cases. Fully rendered traces: AUT-001→AUT-101, INT-103-v01, AGT-201-v01 |
| `data/draft/B001/` | First datagen batch: INT-301, REL-301, OVS-301 × 4 lives (restyle, trap, 2 flips) = 12 rendered traces, with right-card, revised-card (r1) and decoy replies. Eval-only. `CHECK-REPORT.md` = acceptance run |
| `code/datagen/` | Datagen pipeline: `run_stage.py` (stages reference, revised, live, render, reply, critic), `llm.py` (openrouter/ bedrock/ dry/ backends + allowlist), `check_batch.py` (acceptance), `selftest.py`. Read its README |
| `ideas/schema-mvp-2026-09-30/code/mvp.py` | v2.6 validator, card renderer (`card`, `card --spine`), scorer (`reply-score`, `floors`, `trace-check`). The datagen pipeline imports it by path |
| `code/{eval,harness,inference,training}/`, `data/{cases,scenarios}/` | **Empty** — to be built |
| `context/reward/v2/` | `reward_v2.py` (Oct 13): parse → match tool calls → gate → score; `score_completion(completion, gold)`; TRL adapters; 107 tests; `reward-v2-notes.md` |
| `context/reward/observe/` | `observe_v2.py` + write-up: judge-aligned fact matching (two Choice passes, Hungarian) for the enumeration/mapping terms. Prototype |
| `context/training/` | Training plan v1 (Oct 1) and the consolidated "How to Train Analogical Reasoning" v1–v3 (v3 = Oct 13, latest) |
| `context/evaluation/`, `context/proposal/` | Evaluation v1; proposal sections v6 |
| `context/research/` | Research notes incl. `20-open-recipes-and-costs.md`, `21a/21b` model surveys (Granite 4.2 8B vs Qwen3.5-9B, RLVR) |
| `context/seeds/hard-calls-v1/` | 100 natsec case sketches (older v6-style schema: options, factors, holding, flip_rules, downplay_trap…). Seeds for the `reference` stage. Cyber operations are not covered |
| `papers/` | PDFs of the papers read for the project |

## Known drift (reconcile before training; mostly irrelevant to today's untrained eval)

1. **Reply format.** Data in this repo (v2.6) pairs each live with a *mapping* reply (`frame / fit / compare / new
   / carry / decide`), scored by `mvp.py reply-score`. Peter's later pipeline (v7, Oct 13) replaces it with the
   seven-step reply above. `reward_v2.py` implements an intermediate version (sections `facts_enumeration,
   facts_mapping, consideration_mapping, reasoning, verdict`; requires `confidence`). Before SFT: update the
   parser/gate to v7's section names and buckets, drop `confidence` and calibration, and regenerate SFT targets
   in v7 form. **Ask Peter to confirm v7 is the reply format before doing this.**
2. **Card format.** v2.6 reference cards (considerations `c1…` with fact, favors, value, weight, why; judgment
   prose; would_change / would_not_change / watch_for) vs the v7 example's case (explicit `facts` list,
   considerations citing fact ids, `REF1-` ids, equities injected separately). v7's fact mapping needs case fact
   ids, which v2.6 cards don't have. Decide with Peter whether to add a facts list to the reference template.
3. **Equities.** v7 injects a short equities list; v2.6 uses one of 28 shared `value` ids per consideration. Map
   values → equities.
4. `llm.py` refuses AWS credentials that resolve to instance/env credentials (a guard written for a sandbox). On
   this EC2 box the instance role `FiroInstanceRole` would be refused for Bedrock. Use OpenRouter, or ask Peter
   before relaxing the guard.
5. `reward_v2.py` lives in `context/`; when the eval/training code needs it, copy it into a real package
   (e.g. `code/bench/`) and keep the `context/` copy as the frozen reference.

## Environment

- AWS EC2 `g6e.2xlarge` (1× NVIDIA L40S, 48 GB) in us-east-1, Elastic IP 18.211.62.112, name "firo". The Firo Labs
  repo on this box (Peter's LLM-training lab series) likely already has a working torch/vLLM/TRL environment;
  reuse it if so, but keep Benchbook code in this repo.
- Git remote: `https://github.com/banyasp/benchbook-labs` (private). The Mac copy is at
  `~/Desktop/AI/benchbook-labs`. Commit and push from this box often so the Mac and Peter's claude.ai sessions
  see the same code. `.gitignore` keeps `papers/` (PDFs), zips and .docx out.
