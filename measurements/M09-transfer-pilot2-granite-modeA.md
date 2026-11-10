# M09 · Transfer pilot 2, Granite thinks first (mode A)

**Status: PARTIAL**, still running.
- **This snapshot.** The first pass is complete: sample index 0 of all 151 schedule items (28 no-case + 123 cells),
  out of k=8.
- **Taken.** 2026-11-10 20:29 UTC (`results/transfer/MODE-COMPARE-idx0-20261110.md`).
- **Running.** Started 2026-11-10 19:03 UTC; expected to finish around 2026-11-11 05:00 UTC (GPU KV cache saturated,
  about 216 tokens/s).
- **ABORTED earlier attempt.** 60 samples with a 12,000-token budget, 16:41-19:02 UTC, archived at
  `results/transfer/versions/pilot2-modeA.v1-12k-tokens-aborted/`. At 12,000 tokens the free thinking truncated 3 of
  the first 6 flip replies (up to 107,000 characters of thinking), so it was restarted at 20,000. The earlier
  queued design (flip, transfer and no case only, k=4) was widened to all arms at k=8 (`config.json` → `note`).

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

## How
- **Run.**

  ```
  PYTHONPATH=code .venv/bin/python -m eval.allpairs run --run results/transfer/pilot2-modeA --cells results/transfer/pilot2-modeA/cells.json --mode A -k 8 --max-tokens 20000 --concurrency 24
  ```

  Detached with `nohup setsid`; log `logs/pilot2-modeA.log`.
  - In mode A, generation starts at the `<think>` opener with no YAML prefill (`code/harness/episode.py`,
    `render`). Mode C appends `kind: fact_enumeration` after the opener. The prompts are otherwise identical.
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

## Key observations (provisional: one reply per cell)
- **Thinking first helps a little everywhere.** Granite matches Luna on its own case, but no difference is
  statistically clear yet.
- **Granite now notices the flip condition** (63% mention it in free thinking) and thinks twice as long on flip cells,
  yet it still copies the flipped case 45% of the time and declares `flips` only 15% of the time.
- **Contamination is about unchanged** (28% → 49% vs 39% → 56% in mode C), and Granite calls the changed consideration
  "matched" more often (33%). Room to think does not stop it from reinterpreting its own considerations to fit the
  case. That points to a reasoning disposition of the small model, not the YAML format.
- **To update.** Re-run `mode_compare` without `--max-idx` when the run completes (k=8), and replace this snapshot.
