# M20 · 2026-11-15 · Memorization check: SFT gen1 with no case on its own training scenarios

**Status: COMPLETE.**

## Question

Peter asked whether the gen1 adapter memorized its training scenarios. Every training prompt shows X1's trace, and
the target ends in X1's gold choice. Each train X1 appears in 2 to 9 SFT rows, one per arm. If the adapter
memorized trace → answer, then with **no case** it should be far more accurate on train X1s than on unseen val X1s,
and more accurate the more rows it saw.

## Data

- Train: `results/pairs-v1/eval-train-nocase/cells-train-x1.json`, the 438 gen1 train X1s (351 families). Only the
  no-case control is run (`--control-only`), k = 2, so 876 replies per model.
- Val (the comparison): the no-case control rows of M17, `results/pairs-v1/eval-val/{base,sft-final}-v4B`. That is
  61 val X1s (51 families), k = 4, 244 replies per model. Train and val share no X1 and no family.
- Runs (registered in `measurements/runs.yaml`, M20):
  - `results/pairs-v1/eval-train-nocase/base-v4B`: base Granite 4.2 8B.
  - `results/pairs-v1/eval-train-nocase/sft-final-v4B`: plus the LoRA `results/sft/run-gen1/adapter` (the same
    adapter as M17's "SFT final").

## Method

- Command: `scripts/sft_train_nocase_chain.sh` runs `eval.allpairs run --cells cells-train-x1.json --control-only
  --model {base,sft} --mode B --scaffold v4 -k 2 --max-tokens 8000 --concurrency 12`. The settings and prompt format
  are identical to M17. Both models ran together on 2026-11-15 from 15:21 to 17:22Z.
- Scoring: allpairs-scoring-v4 on every reply. The key is X1's gold.
- Tables: `PYTHONPATH=code .venv/bin/python -m eval.analysis.m20_train_nocase` writes
  `results/pairs-v1/eval-train-nocase/m20-report.md` (+ `.json`).
  - Accuracy is X1-averaged, with a 95% family bootstrap (B = 2000).
  - Gain is SFT minus base, per X1.
  - The gain gap is the train gain minus the val gain. Its bootstrap resamples train and val families
    independently.
  - SFT rows per X1 come from `results/sft/gen1/sft.jsonl`.
- LLMs:
  - Policy: Granite, base and LoRA, on local vLLM.
  - Judge: Jev Choice, used only when a reply's options are not an exact-text match (scoring v4).
  - No Claude-read numbers.

## Results

**No-case choice accuracy, %:**

| Split | X1s | base | SFT final | gain (SFT − base) |
|---|---|---|---|---|
| Train (seen in SFT) | 438 | 53.5 [49.5, 57.6] | 64.8 [61.3, 68.5] | +11.3 [7.1, 15.7] |
| Val (unseen) | 61 | 51.6 [41.5, 61.5] | 57.8 [48.7, 66.0] | +6.1 [−3.9, 16.1] |

- **Gain gap** (train gain − val gain): **+5.2 [−5.4, 16.2]**.
- SFT, train minus val: +7.1 [−1.9, 15.9]. Base, train minus val: +1.9 [−8.4, 12.9].
- **Among replies with a verdict** (pooled, which separates format fixes from better choices):

  | Split | base | SFT | gain |
  |---|---|---|---|
  | Train | 55.4 | 65.0 | +9.6 |
  | Val | 52.9 | 58.0 | +5.1 |

  Base gave no verdict on 30 of 876 train replies and the adapter on 2. On val, base gave none on 6 of 244 and the
  adapter on 1.

**Train gain by the number of SFT rows the X1 had:**

| SFT rows | X1s | base | SFT final | gain |
|---|---|---|---|---|
| 2-3 | 89 | 51.7 | 62.9 | +11.2 [1.6, 20.6] |
| 4-5 | 171 | 51.2 | 63.2 | +12.0 [4.6, 19.1] |
| 6-7 | 149 | 55.4 | 68.1 | +12.8 [5.7, 20.0] |
| 8-9 | 29 | 63.8 | 63.8 | +0.0 [−17.2, 15.5] |

**Per-X1 transitions:**

| Split | X1s | SFT better | SFT worse | same | base always wrong → SFT always right | base always right → SFT always wrong |
|---|---|---|---|---|---|---|
| Train | 438 | 157 | 88 | 193 | 44 | 14 |
| Val | 61 | 21 | 15 | 25 | 1 | 0 |

## Readings (Claude)

- **No sign of rote memorization.** The adapter trained on each of these scenarios 2 to 9 times, always with the gold
  answer at the end. Without a case it still gets only 64.8% of them right, and it does worse than base on 88 of the
  438. A model that had stored trace → answer would be near the ceiling here.
- **Seen scenarios may gain slightly more than unseen ones** (+11.3 vs +6.1). The gap of +5.2 has an interval of
  [−5.4, 16.2], which includes zero, so it is not established. Even taken at face value, it is small next to the
  with-case gains in M17. In-domain flip, for example, went from 3.8 to 95.3.
- **No dose-response.** The gain is flat from 2 to 7 rows (+11.2, +12.0, +12.8), and the 29 most-exposed X1s show
  +0.0. Memorization should grow with exposure.
- So the with-case gains in M17 come from reading the case, not from recalling the scenario. The flip arms make the
  same point: there the case's verdict is wrong, and no-case accuracy on the same scenarios is about 65%.

## Caveats

- Train uses k = 2 and val uses k = 4. Both are X1-averaged, but per-X1 values on train are coarser (0, 0.5, 1).
- Each SFT prompt included a case. A no-case prompt is a different input, so this tests whether the trace alone
  recalls the answer, which is the memorization Peter asked about. It does not test recall when a case is present.
- The 8-9 row bin has 29 X1s, and its base accuracy is higher (63.8). That bin is noisy.
- Final adapter only. Checkpoint-300 was not run on train.
