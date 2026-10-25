# Decisions for the EC2 session — 2026-10-25 (Peter, via his claude.ai session)

> **Update (later on 2026-10-25):** (1) SFT golden reasoning is written by a **stronger teacher model, never the
> base model** (overrides the PDF); Peter names the teacher later — make it a config setting. (2) The
> open-weight-only authorship allowlist is **lifted**: relax `models.yaml` to record provenance only. Where this file
> says "allowlisted" or "training-bound", read it in that light.

Read this after `CLAUDE.md`, `context/PDF-RECONCILIATION-2026-10-25.md` and `HANDOFF-2026-10-25.md`. Where this
file and the handoff differ, this file is newer. Proceed with Step 2; don't wait on the open items at the end.

## Your three questions

1. **Relax `llm.py`'s instance-credential guard: yes, on this box.** Allow the instance role when an explicit
   opt-in is set (e.g. `BENCHBOOK_AWS_ALLOW_INSTANCE_ROLE=1`, region `us-east-1`) and keep refusing elsewhere.
   Record the credential source (`instance-role:FiroInstanceRole`) in `provenance.jsonl`. Save the old file in
   `versions/` first and run `selftest.py` after.
2. **Pin boto3: yes.** Add it to `requirements-gpu.in` and the lockfile; note the `python-dateutil` downgrade in
   the commit message.
3. **Judge: stays TypeSafe Jev via OpenRouter** (`typesafe/jev-1.14`, pinned; Choice for fact and option
   alignment, Noul for yes/no). Peter is adding `OPENROUTER_API_KEY` to the box. Reason: the scorers' two-pass
   alignment needs a **probability distribution** over options, and Bedrock's hosted models return no token
   probabilities (only Custom Model Import does). Keep the judge behind the one cached interface. Later, a second
   judge (Cloudflare Clef-flash, open weights) will be used only to validate the judge on ~150 hand-checked pairs.
   **gpt-oss-120b on Bedrock is for generative work**: converting cases, and later ingestion, case authoring and
   trace rendering. Being on the allowlist, its output can become training data after Peter's review.

## Scoring and format (also recorded in the reconciliation file)

- The PDF is ground truth.
- **The decision is scored from the verdict's `choice`** (translated to gold ids, exact match). Tool calls and
  says/does consistency are out of scope (future work).
- **`via` stays** in the verdict: required for `flips` (the served case's `would_change` id(s) that fired), null
  otherwise. Check the choice against that item's `then:`; partial-credit amounts belong to the reward.
- **Greedy** fact assignment (PDF p. 21), not Hungarian; the PDF's found/extra score.
- **No `confidence`.** Nothing after `not_governed` is scored.
- **The reward function is TBD (Peter).** Every scorer is a separate function returning its own value; no
  weights, no combination, no fixed gate penalty.
- Policy model: Granite 4.2 8B. Qwen3.5 9B later.

## Step 2: the split is approved, with these changes

- **2a schemas first**, with the PDF's REF1/journalist example as the reference test. Add `via` to the verdict.
- **2b library:** convert the pilot's cases to the PDF case format **first** (INT-301, REL-301, OVS-301 and
  their `-r1` revised cards, AUT-001, INT-103, AGT-201), because Checkpoint 2 runs on converted cards. Use
  **gpt-oss-120b on Bedrock** for the conversion (so the converted cases aren't Claude-authored), validate with the
  2a models, flag each as `status: converted, needs_review`, and list three for Peter to spot-check. Follow
  `context/DATA-PIPELINE-DESIGN-v1.md` sections 4–5 for ids and the index schema; today build the layout, the
  oracle retriever and the converter, and stub the structural index.
- **2c harness:** as proposed (role and tool-message format as settings; draft the analogical-reasoning prompt
  from PDF pp. 11–13 for Peter's review).
- **2d scorers (Opus):** one function per row of the PDF's scoring table, including the **options-enumeration
  score** and **judge-based alignment of the model's own option ids to the gold ones** (your shortcut-cue finding).
- **2e eval + training scaffolding:** as proposed; CPU-only checks today.
- Subagent models as you proposed (Sonnet for 2b/2c/2e, Opus for 2d). Worktrees, one directory each, keep every
  version, flag shortcut cues, write no training-bound data.
- **2f data ingestion is ON HOLD.** Peter is designing it in claude.ai. Bedrock access is verified; build nothing
  else there.
- Don't touch the Firo venv; note its flashinfer/Python mismatch as a follow-up.

## Checkpoint 2 (base Granite, untrained) — what to run

**Arms (PDF grid):** no reference / relevant case / augmented case (the `-r1` revised card; gold = the revised
card's answer) / decoy — each **with and without** the analogical-reasoning prompt.

**Reasoning modes (new): run all four on the pilot.**
- **A:** thinking on (free prose in `<think>`), structured `kind:` reply after `</think>`.
- **B:** thinking off (`enable_thinking: false`), structured reply.
- **C:** structured `kind:` documents **inside** `<think>` (prefill the assistant turn with
  `<think>\nkind: fact_enumeration\n`), then the verdict after `</think>`.
- **C′:** like C, but free-text notes are allowed between the YAML documents inside `<think>`; the scorer reads only
  `kind:` documents.

The parser must read the structure from inside or outside `<think>`. Cap generation (e.g. 12k tokens) so thinking
modes can't run away.

**Faithfulness test (PDF, "manipulation of analogical reasoning"):** on a subset, intervene mid-reply (edit a
consideration's weight or bucket in the mapping, or swap in the revised card), let the model continue, and record
whether the verdict changes. Report the change rate per mode. Prediction to test: mode A's verdicts are the least
sensitive (decided in free thinking; the structure is after-the-fact).

**Sampling and statistics:** 5–8 samples per item per arm per mode, Granite's recommended sampling settings,
confidence intervals by resampling whole case families. Store per-sample perturbation features (variant type,
operator, number and kind of facts touched) so any distance weighting can be applied later.

**Report** in `results/RESULTS-2026-10-25.md`, per mode × arm: choice accuracy, format compliance, options
enumerated (and gold-option omissions), relation and `via` accuracy, tokens and time, faithfulness change rate,
shortcut cues seen. This is the PDF's Checkpoint 2.

## Open with Peter (don't block on these)

- `partner_relationship` vs the PDF example's equities list (reconciliation A6).
- Whether applicability keeps `decisive_in_case` (A4).
- Distance-axis weights.
- The reward function.
