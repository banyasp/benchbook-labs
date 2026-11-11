# M09 · Transfer pilot 2, Granite thinks first (mode A)

**Status: COMPLETE** (k=8), 2026-11-11 09:14 UTC: 1,208 samples, 0 errors.
- Ran 2026-11-10 19:03 UTC to 2026-11-11 00:19 (k=4); paused for M11's Granite guided/free runs; resumed 03:52 to 09:14
  UTC (`scripts/scaffold_gpu_chain.sh`, log `logs/scaffold-gpu-chain.log`).
- Final comparison: `results/transfer/MODE-COMPARE-pilot2-k8-20261111.md` (all three runs at k=8). The first-pass
  snapshot below is kept for the record; the k=8 tables supersede it.
- **ABORTED earlier attempt.** 60 samples with a 12,000-token budget, 16:41-19:02 UTC, archived at
  `results/transfer/versions/pilot2-modeA.v1-12k-tokens-aborted/`. At 12,000 tokens the free thinking truncated 3 of
  the first 6 flip replies (up to 107,000 characters of thinking), so it was restarted at 20,000.

## What was measured
- **Question** (Peter, 2026-11-10). Does letting Granite think in free prose before writing the YAML (as Luna does with
  hidden reasoning) close the gap to Luna? In particular, does it stop the flip-arm copying and the contamination?
- **Design.** Same cells, traces (render.v5), equities and k as M06 and M07. Only the reasoning mode (A) and the token
  budget (20,000; M07 used 12,000 and M06 16,000) differ.

## What was observed

**First pass only** (one reply per cell), all three runs restricted to sample index 0 for a fair comparison:

| Arm | Granite C (M07) | Granite A (this) | Luna (M06) |
|---|---|---|---|
| no case | 39% [22-59] | 54% [36-71] | 64% [46-82] |
| own case | 82% [67-96] | 93% [83-100] | 93% [81-100] |
| transferred sister | 75% [58-91]; copies 75% | 80% [67-92]; copies 80% | 88% [74-98]; copies 88% |
| flipped sister | 25% [10-42]; copies 60% | 38% [20-57]; copies 45% | 82% [65-95]; copies 8% |
| other anchor's sister | 50% [33-69] | 46% [30-66] | 68% [52-83] |

Paired per-X1 differences, mode A − mode C (sample 0): no case +14 [−4, +31]; own case +11 [−3, +28]; transfer +5
[−12, +23]; flip +12 [−10, +35]; decoy −4 [−24, +17]. None excludes zero yet. Luna − mode A on the flip arm: +45
[+20, +70].

**Flip arm mechanics:**

| Measure | Granite C | Granite A | Luna |
|---|---|---|---|
| Declares `flips` with the right `via` | 0% | 15% | 48% |
| Flipped consideration: corresponding / matched / case_only / absent | 44 / 22 / 22 / 11% | 44 / 33 / 11 / 11% | 85 / 0 / 15 / 0% |
| Reasoning or applicability mentions a flip condition | 30% | 41% | 37% |
| Free thinking mentions a flip condition | n/a | 63% | n/a (hidden) |
| Mean thinking characters on the flip arm | 15,417 | 30,424 | n/a |
| Truncated on the flip arm | 7% | 4% | 0% |

**Contamination** (see M08 for the definition):

| Arm | Granite C | Granite A | Luna |
|---|---|---|---|
| no case | 39% | 28% | 20% |
| flipped sister | 56% | 49% | 23% |

## Final results (k=8, all three runs)

From `results/transfer/MODE-COMPARE-pilot2-k8-20261111.md` (`python -m eval.analysis.mode_compare`, no `--max-idx`).

| Arm | Granite C (M07) | Granite A (this) | Luna (M06) |
|---|---|---|---|
| no case | 45% [32-60] | 48% [35-61] | 66% [51-79] |
| own case | 81% [72-88] | 90% [82-97] | 91% [83-98] |
| transferred sister | 73%; copies 73% | 81%; copies 81% | 86%; copies 86% |
| flipped sister | 19%; copies 57% | 31%; copies 49% | 76%; copies 14% |
| other anchor's sister | 46% | 48% | 70% |

- **Paired, mode A − mode C:** no case +3 [−5, +10]; own case +9 [+4, +16]; transferred +7 [0, +16]; flipped +11
  [+3, +20]; other anchor's case +2 [−6, +11].
- **Luna − mode A:** no case +18 [+4, +32]; own case +1; transferred +5 [−3, +13]; flipped +45 [+28, +62]; other
  anchor's case +22 [+9, +35].
- **Truncation** falls from 1-9% (mode C) to 0% on every arm. Thinking is about 1.6x longer (flip arm 29,000 vs
  16,000 characters).
- **Flip mechanics:** declares `flips` with the right `via` 8% (C 3%, Luna 52%). Flipped consideration marked
  corresponding 45% (C 36%, Luna 88%) and matched 31% (Luna 1%). Free thinking mentions a flip condition 59%.
- **Contamination**, own considerations favoring the flipped case's verdict: no case 30%, flip 45% (C 36% → 50%; Luna
  24% → 22%).
- **Other anchor's case:** Luna declares `not_governed` 97% of the time; Granite A does 8%, follows 47% and
  distinguishes 38%.

**Reading.**
- Thinking first is a real but modest gain for Granite: significant on own case (+9) and flipped (+11), and it ends
  truncation. It closes the gap to Luna where the answer is in the case (own, transferred). It does not close it
  where the model has to reason against or without the case (no case −18, flipped −45, other anchor's case −22).
- The flip failure survives free thinking. Granite notices the flip condition in its thinking (59%) but rarely acts on
  it (8% declare flips), and its own considerations still bend toward the case (45%). With M11 (the scaffold does not
  matter either), this places the flip weakness in the model, not in the format or the token budget.
- Granite rarely declines an irrelevant case (8% not_governed vs Luna 97%). That is a second thing training must teach.

## How
- **Run.**

  ```
  PYTHONPATH=code .venv/bin/python -m eval.allpairs run --run results/transfer/pilot2-modeA --cells results/transfer/pilot2-modeA/cells.json --mode A -k 8 --max-tokens 20000 --concurrency 24
  ```

  Detached with `nohup setsid`; log `logs/pilot2-modeA.log`.
  - In mode A, generation starts at the `<think>` opener with no YAML prefill (`code/harness/episode.py`,
    `render`). Mode C appends `kind: fact_enumeration` after the opener. The one prompt difference is the mode line
    from `code/harness/prompts/modes.v1.yaml`, appended to the format spec:
    - A: "Think through the decision freely first. Then, after your thinking, write the YAML documents as your reply."
    - C: "Your thinking is the structure. Write the YAML documents inside your thinking…"
  - The parser takes the YAML after `</think>`. When a reply truncates, it falls back to drafts inside the thinking.
- **Comparison.**

  ```
  PYTHONPATH=code .venv/bin/python -m eval.analysis.mode_compare --max-idx 0 --out results/transfer/MODE-COMPARE-idx0-20261110.md
  ```

  It is deterministic. "Free thinking mentions a flip condition" is a regex (`would_change`, `flip condition`,
  `REF1-flip`, `flip1`) over the thinking prose before any YAML draft.
- **LLMs.**
  - Policy: Granite on local vLLM (bf16).
  - Judge: Jev Choice for the option mapping, and through it for contamination.
- **Data.** `results/transfer/pilot2-modeA/` (`config.json`, `samples.jsonl`, `raw/`, `details/`). The report is
  written when the run ends.

## Key observations from the first pass (provisional, superseded by the k=8 results above)
- **Thinking first helps a little everywhere.** Granite matches Luna on its own case, but no difference is
  statistically clear yet.
- **Granite now notices the flip condition** (63% mention it in free thinking) and thinks twice as long on flip cells,
  yet it still copies the flipped case 45% of the time and declares `flips` only 15% of the time.
- **Contamination is about unchanged** (28% → 49% vs 39% → 56% in mode C), and Granite calls the changed consideration
  "matched" more often (33%). Room to think does not stop it from reinterpreting its own considerations to fit the
  case. That points to a reasoning disposition of the small model, not the YAML format.
- **To update.** Re-run `mode_compare` without `--max-idx` when the run completes (k=8), and replace this snapshot.
