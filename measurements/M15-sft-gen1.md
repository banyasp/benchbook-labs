# M15 · 2026-11-13 · SFT target generation, full train set (gen1)

**Status: COMPLETE** (generation). The random-arm flip-condition defect below awaits Peter's decision.

## Question

What does the chosen SFT pipeline (M13 addendum) yield at scale? Measured: how often Granite's guided W/V passes,
how often the run falls back to Luna's text, and the random arm's drop rate and quality.

## Data

- Cells: `pairs-v1` full (M14), filtered by `pipeline.sft.generate select`. Arm is not revised (Peter, 2026-11-13:
  for SFT, revised is the same as self). X1 has a trace. X1 and any served anchor are train-split and not held out.
  Result: 2,217 cells over 438 X1 anchors.

  | self | transfer | transfer_flip | same_domain_flip | noflip | neighbor | random |
  |---|---|---|---|---|---|---|
  | 438 | 258 | 286 | 507 | 246 | 266 | 216 |

  The random arm has fewer cells because its served anchor must also be train.
- Pipeline: `code/pipeline/sft/generate.py` (stages: select, write, wv, assemble), format v3, mode B. Granite W/V uses
  k=2 per round, up to 2 rounds. Kept iff the structure check passes, Jev "supports" passes and Jev "same argument as
  Luna" passes; otherwise Luna's own target. Random arm: Granite without the case, k=4, kept iff it parses, the
  choice is live and Jev says W supports its own choice; otherwise the cell is dropped.
- Outputs, on the box only: `results/sft/gen1/` (`cells.json`, `write.jsonl`, `wv.jsonl`, `sft.jsonl`, `report.md`).
  Console `/sft` → `results/sft/gen1`. Logs: `logs/sft-gen1-{write,wv}.log`.
- Run 2026-11-13 05:00–09:49Z. The W/V stage was restarted once (06:15Z) to go from 8 to 16 workers; it resumed
  from its output.

## Results

| arm | cells | Luna ok | W/V done | Granite guided | Luna fallback | Granite no-case | dropped |
|---|---|---|---|---|---|---|---|
| self | 438 | 438 | 438 | 438 | 0 | | |
| transfer | 258 | 257 | 257 | 253 | 4 | | |
| transfer_flip | 286 | 283 | 283 | 253 | 30 (10.6%) | | |
| same_domain_flip | 507 | 507 | 507 | 451 | 56 (11.0%) | | |
| noflip | 246 | 246 | 246 | 242 | 4 | | |
| neighbor | 266 | 265 | 265 | 262 | 3 | | |
| random | 216 | 214 | 214 | | | 211 | 3 |
| **all** | 2,217 | 2,210 | 2,210 | 1,899 | 97 | 211 | 3 |

**2,207 SFT rows** (`sft.jsonl`): 1,899 Granite-guided (86%), 97 Luna (4.4%), 211 Granite no-case (random).

- **Luna write:** 2,210/2,217 accepted. Six are skips at gold-building (4 aligner fact maps not one-to-one; 1
  transfer_flip whose X2 has no would_change leading to X1's gold; 1 random cell the aligner says governs). One
  transfer_flip write failed the structure check on both tries.
- **Granite guided samples:** 4,350 drawn, 3,512 pass structure (81%); 1,817 of 1,996 cells settled in round 1.
  - Structure rejections: mostly the relation on flip cells (gold flips; Granite wrote distinguished 183, follows
    178), then verdict YAML (unbalanced brace 127, verdict missing 123, flip_conditions not a mapping 89).
  - Gates on structure-passing samples: supports 3,502/3,512, same argument 3,335/3,512 (95%).
- **Luna fallbacks (97):** 81 had no structure-passing sample, almost all flip cells where Granite would not say
  `flips`, the M13 finding. 16 passed structure and supports but failed "same argument".
- **case_approach (chosen Granite targets, 1,899):** Jev case-account P median 0.94 (≥0.5 in 1,843); 1 starts as a
  directive; median 3 REF1 ids and 90 words. 138 (7%) cite LIVE ids, against the guidance.
- **Random arm:** 211/214 kept (first sample in 156). Granite's no-case choice equals X1's gold in 166/211 (79%).
- **Lengths (Granite tokenizer):** prompt median 6,288 tokens (max 7,354); completion median 2,516 (p95 3,205,
  max 4,194); longest prompt+completion 11,349. Total completion tokens 5.65M. No duplicate rows (sha256).
  2,207 distinct prompts.

### Defect: random-arm flip conditions contradict Granite's choice

`splice_random` puts X1's gold `flip_conditions` into the verdict (as on every arm), but the choice is Granite's own.
In 45 rows the choice differs from gold. In 37 of them a would_change item says "then <the option just chosen>",
e.g. PV1-full-00763 (chooses LIVE-O1; LIVE-flip1 "then LIVE-O1"). Granite's own verdict carries its own flip
conditions in all 45. Fixing it needs no new generation (re-splice from `wv.jsonl` samples), but which rule to
use is Peter's call.

### Claude-read (4 rows, not a systematic rating)

- PV1-full-01105 (same_domain_flip, Granite guided): applicability, case_approach and weighing agree. The flip
  item's condition is stated and tied to LIVE facts. Good.
- PV1-full-02856 (transfer_flip, Luna fallback): coherent; it lists LIVE-C2 as decisive while calling it "weaker".
- PV1-full-00763 (random, choice ≠ gold): the defect above. Granite's no-case W is weaker. It weighs by
  consideration *kind* names ("mission_effect") instead of LIVE ids, and its course is a hybrid of the two options
  (R96).
- PV1-full-02927 (same_domain_flip, Granite guided, LIVE ids in case_approach): case_approach runs to
  about 170 words and applies the case to the live facts (applicability's job). The weighing mislabels an id ("from
  REF1-C3 (LIVE-C2)"). Jev passed both gates.

## Commands

    PYTHONPATH=code .venv/bin/python -m pipeline.sft.generate select   --run results/sft/gen1
    PYTHONPATH=code .venv/bin/python -m pipeline.sft.generate write    --run results/sft/gen1 --workers 16
    PYTHONPATH=code .venv/bin/python -m pipeline.sft.generate wv       --run results/sft/gen1 --workers 16 [--follow]
    PYTHONPATH=code .venv/bin/python -m pipeline.sft.generate assemble --run results/sft/gen1

## LLMs in the loop

- GPT-6 Luna on Bedrock, not metered (known gap):
  - aligner (`sft_aligner`) for transfer, neighbor and random;
  - writer (`sft_writer`, 2,217 cells, ~1.0 tries each).
  - Estimate from list prices: about $20.
- Base Granite 4.2 8B on local vLLM: guided W/V (4,350 samples), no-case W/V (856 samples).
- TypeSafe Jev 1.14 (OpenRouter): supports, same argument and case_account gates.
- Claude: the four-row read above, and the counts (scripts run ad hoc over `wv.jsonl` / `sft.jsonl`).
