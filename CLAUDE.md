# Benchbook Labs — standing context for Claude

*Written 2026-10-25 from Peter's claude.ai project ("Recruiting and Learning") so a Claude Code session on the
EC2 box starts with the same context. Read next, in order: `DECISIONS-2026-10-25.md` (latest rulings),
`BUILD-BRIEF-2f-2026-10-25.md` (tonight's data-pipeline work order), `HANDOFF-2026-10-25.md` (the day's earlier plan),
`docs/RISK-REGISTER.md`.*

> **Ground truth: `context/Benchbook-Research-Plan-v0.4.pdf`.** Where any code, example, spec or doc in this repo
> disagrees with the PDF, the PDF wins. Known disagreements are listed in
> `context/PDF-RECONCILIATION-2026-10-25.md`; read it before touching the scorer, the reply format or the data.

## The project in one paragraph

**The Benchbook: Alignment at the Edge** (Peter Banyas). A harness monitor watches an agent; when the agent nears
a consequential decision, the harness pauses it and injects a short list of the deployer's *equities* plus a
*reference case* (an SME's worked decision: facts, considerations, weighing, verdict, flip conditions). The agent
reasons from the case by analogy and then acts through tool calls. **Thesis:** LLMs that are both (1) trained to
reason analogically and (2) served relevant exemplar cases at inference time make more aligned choices out of
distribution than either alone. Selling points: pluralism (each deployer steers with its own tradecraft), privacy
(cases never enter a lab's training data), online edits (change the library, behavior changes now),
generalizability (cases transfer across domains with the same structure), explainability (the trace cites
precedent). Policy model: IBM Granite 4.2 8B (primary), Qwen3.5 9B as the comparison model (PDF), with one
LoRA adapter. Full plan: `context/Benchbook-Research-Plan-v0.4.pdf`.

## How Peter works (follow these)

- **Think with him.** He welcomes questions at the start and mid-work. Ask when a decision is his (see the open
  decisions in the handoff); don't silently pick. Recommend an option when you have a view.
- **Keep every version.** Never overwrite a draft, spec, prompt or result: copy the old one into a `versions/`
  folder next to it (name it `<file>.vN-<what changed>.<ext>`) before editing. This repo already follows that.
- **His own writing is authoritative.** Documents Peter wrote beat AI-generated derivatives. Everything under
  `context/` and most of `ideas/` was drafted *with* Claude in earlier sessions; treat it as strong context, not
  law, and flag contradictions instead of resolving them yourself.
- **Precedence:** the v0.4 PDF first; then `examples-v21/templates/` (the v2.6 data spec) over the datagen
  pipeline — the pipeline changes to fit the spec, never the reverse. Where the v2.6 spec disagrees with the PDF
  (case format, reply format), the PDF wins; see the reconciliation file.
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

- **Log risks as you find them.** `docs/RISK-REGISTER.md` records every assumption, risk and inference (and how
  to observe it). When you hit a new one — a shortcut cue, a data artifact, a judge failure — append an entry the
  same day. Never delete entries.

## Peter's standing design decisions

- The harness injects the case; the agent never fetches it with a tool call.
- Default agent stance is true long-horizon autonomy: it figures out what to do and does it. Always escalating to
  a human is a crutch. "Escalate when no close case exists" may be an optional deployer setting, never the default.
- Scenarios are deliberately simple in form; judgment, values and tradecraft live in prose, not in an if-tree.
- **Agent pipeline (PDF v0.4, Fig. 3):** trace → [injected] equities → [injected] case → `fact_enumeration`
  (frame: question, decider, my_role; facts with ids, kind, status; options) → `fact_mapping` (frame comparison
  same | same_kind | different; options map; `matched / corresponding / live_only / case_only`) →
  `consideration_enumeration` (facts → equity → favors → weight → why) → `consideration_mapping`
  (`matched / corresponding / live_only / case_only`, with `role`; for a significant case-only consideration,
  either reason without it or state an assumption, usually the "normal" ceteris-paribus state) →
  `applicability` (frame, `governs`, why) → `reasoning` (case_approach, weighing, tradecraft, uncertainty,
  handoff, tempting_wrong, rejected) → `verdict` (choice, course, relation, decisive, now, flip_conditions).
  Each step is a YAML document with `kind:`. Worked example: PDF pp. 14-18. (The v7 yaml in `context/schema/` is
  the same example with older names: `discretization`, `altered`, `carried/revised`, plus `confidence`/`via`.)
  Extracting facts before seeing cases is future work.
- Relations: `follows | flips | distinguished | not_governed`. **`not_governed` ends the agent's reasoning, and
  nothing it does after deciding not_governed is rewarded or punished** (he is not training judgment independent
  of the case). Governance is decided on considerations, not fact overlap.
- **No numeric `confidence` in the verdict** (matches the PDF), so the reward has no calibration term.
- **The decision is scored from the verdict's `choice`** (PDF; Peter confirmed 2026-10-25). Tool calls and
  says/does consistency are future work: they test whether a model does what it says, not analogical reasoning.
- **The verdict carries `via`** (added to the PDF, Peter 2026-10-25): for `flips`, the id of the served case's
  `would_change` item that fired; the choice must match that item's `then:`.
- **Fact matching uses greedy assignment** (PDF p. 21), not Hungarian. **The reward function is TBD** (Peter will
  define the weights and combination): build every scorer as a separate function.
- Training: LoRA SFT with loss only on the generated reasoning tokens (trace, equities and cases masked).
  **SFT targets come from rejection sampling the base model** (Peter, evening of 2026-10-25 — back in line with
  the PDF): Granite generates replies with two worked examples in the prompt and *no gold answer*; only samples
  that match gold structure (verdict, relation, `via`, applicability, mapping buckets) are kept. SFT is a warm
  start for format and plain weighing; RLVR on gold structure does most of the teaching. (Earlier the same day:
  "a teacher, never the base model" — superseded.) Then RLVR: GRPO with
  Dr. GRPO normalization, 8 rollouts, KL to the SFT checkpoint. Scoring per the PDF's table (pp. 23-24):
  deterministic checks plus narrow judge calls (Jev Choice to align facts, Jev_Noul for free-text fields like
  frame and course); reasoning prose and applicability-why are never scored. One scorer package shared by TRL
  (training) and Inspect (eval).
- **Eval infrastructure: UK AISI Inspect (`inspect_ai`).**
- **Headline experiment:** alignment (action) accuracy vs. distance from the live scenario to the nearest
  reference case, one curve per arm (base / harness / SFT / SFT+RL), showing alignment generalizes and the arms
  are additive. Distance is computed structured-YAML to structured-YAML, never against traces. Second graph:
  accuracy vs. library size per arm ("scaling law for alignment"). Core generalization first; library-improvement
  work later.
- Cross-domain transfer (structurally similar case from another domain) is the big value-add of analogy; one whole
  domain is held out for the test.
- **The open-weight-only authorship allowlist is lifted** (Peter, 2026-10-25: he is not bound to it). The
  allowlist in `code/datagen/models.yaml` / DATAGEN-SPEC §10 dates from the Sep 29 "plan v2" data work; relax it to
  record-only. Keep recording, per field, which model wrote what (provenance) — that is still required. Before
  training on a closed model's outputs, Peter checks that provider's terms on using outputs to train models.

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

## Known drift

See `context/PDF-RECONCILIATION-2026-10-25.md` for the full list. In short:
1. `reward_v2.py` was written for a pre-v0.4 reply: it would gate-fail every PDF-format reply (section names,
   multi-document YAML, buckets, required `confidence` and `via`), still scores invariance after `not_governed`
   (Peter decided nothing after a decline is scored), and covers only part of the PDF's scoring table.
2. The v2.6 data (examples-v21, B001) has no case fact ids, uses `value` instead of equities, and its replies are
   in the old mapping format. Fine for today's choice/action eval; must be converted for reasoning scores and SFT.
3. `observe_v2.py` matches the PDF's buckets and two-pass Choice design but uses Hungarian assignment and an F1
   score where the PDF specifies greedy assignment and a found/extra weighted sum.
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
