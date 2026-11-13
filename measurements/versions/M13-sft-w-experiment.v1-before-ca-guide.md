# M13 · 2026-11-12 · How to write W for SFT targets: Luna + restate vs Granite's own vs Granite guided by Luna

**Status: COMPLETE** (small-scale pilot, 24 cells; Peter asked for it before choosing the W pipeline for full SFT
generation).

## Question

Peter's SFT design (2026-11-12, CLAUDE.md): the target `F,Q | M_F | K | M_K | applicability | W | V` gets its fixed
parts from gold by code, and its prose (W above all) from Luna writing with the full answer key, after which base
Granite restates it in its own words (to keep the target close to Granite's own distribution). He asked for a
comparison with gold-conditioned rejection sampling (Granite writes W and V itself) on failure rates and quality.

## Data

- 24 pairs-v1 pilot cells, 3 per arm (self, transfer, transfer_flip, same_domain_flip, noflip, revised, neighbor,
  random), X1 with a rendered trace, anchors spread across arms; seeded (`wexp|0`). `results/sft/wexp1/cells.json`.
- Mapping gold by code from operator lineage (`code/pipeline/sft/pairgold.py`); the fact map for transfer / neighbor
  and everything for random from the LLM aligner (role `sft_aligner`, Luna), stored with the cell and reused.
- All outputs: `results/sft/wexp1/` (`write.jsonl`, `granite.jsonl`, `guided.jsonl`, `likelihood.json`,
  `report.md`; on the box only, not in git). The first Granite pass with checker bugs is kept as
  `granite.v1-checker-bugs.jsonl`.

## Variants

| Variant | Who writes W and V | Accept rule |
|---|---|---|
| L | Luna (`sft_writer`, prompt `code/pipeline/sft/prompts/writer.v1.md` = solve teacher.v4 + amendments A1-A3) | full structure check (`pipeline.solve.check.check_reply`) |
| L+R | L, then base Granite restates each prose passage (`sft_restater`, thinking off) | structure check + Jev gates |
| G | base Granite, mode B, after a gold prefill of F..applicability (Luna's mapping prose), k=8 | structure check |
| G+notes | as G, with Luna's reasoning + verdict added to the prompt as "notes from a senior reviewer", k=2 | structure check + Jev gates |
| random arm | base Granite with NO case (the -noref prompt), prefilled with gold F and K, k=4; spliced after Luna's not_governed applicability (Peter's design) | parses |

Jev gates (`targets.gate`): **supports** = Jev Choice over the live options given only W (verdict hidden) picks the
target's choice; **same argument** = Jev Noul, P(yes) >= 0.5 that W makes the same argument as Luna's.
Likelihood (`wexp.w_logprob`): mean log-probability per token of the reasoning document under base Granite, given the
student prompt and the target's own preceding documents (vLLM prompt_logprobs, a forward pass).

## Results

| | L | L+R | G | G+notes |
|---|---|---|---|---|
| cells with an accepted target (21 non-random) | 21/21 | 21/21 | 15/21 | 20/21 |
| accepted samples | 21/21 (all first try) | 21/21 | 96/168 (57%) | 37/42 (88%) |
| flip arms (6 cells) | 6/6 | 6/6 | **0/6 (0/48 samples)** | 5/6 (16/18 samples) |
| Jev supports (accepted) | 21/21 | 21/21 | — | 35/37 |
| Jev same argument as L | — | 21/21 | — | 34/37 |
| text similarity to L, per W field (median) | 1 | 0.83 (12/105 fields identical) | — | 0.13 |
| mean logprob/token of W under Granite (median) | -1.45 | -1.51 | -0.54* | -0.78 |
| W words (median) | 275 | 283 | 256 | 223 |

\* G's samples were drawn from Granite itself at T=1, which inflates its likelihood; L, L+R and G+notes are comparable.

- **L+R does not do what restating is for.** Granite copied Luna's passages (median similarity 0.83; whole fields
  verbatim in 12 of 105) and the restated W is *less* likely under Granite than Luna's (median -0.03 nats/token;
  more likely in only 6/21). In 2/21 cells the restatement dropped almost every id citation (`ids_lost` in
  `granite.jsonl`), which the Jev gates do not catch. Earlier restate prompts failed differently (YAML list output
  broke; a two-line example was cloned and Granite stopped after `[2]`, the O17 lesson); prompt fixed, all 24 pass now.
- **G (Granite alone) never says `flips`.** On flip arms it reached the gold choice in 28/48 samples but labelled the
  relation follows or distinguished every time. Rejections elsewhere were mostly relation and parse. Quality (Claude-
  read, 15 accepted samples): `case_approach` is usually a directive ("Weigh X against Y", "Request input …") rather
  than how the case weighed its considerations (about 11/15); W rarely says which of the case's conditions recur here
  or which would_change items fail to hold. It reasons, but not by analogy.
- **G+notes is the best of the four.** Granite writes in its own words (similarity 0.13; +0.66 nats/token more likely
  than Luna's text, higher in 36/36), keeps Luna's argument by Jev (34/37), reaches flips with `via` (16/18), and its
  W still names the case's decisive condition and the fired flip item (Claude-read: cells 00451, 00148). It is shorter
  and states weights in parentheses ("LIVE-C2 (strong)"); it keeps about 43% of Luna's id citations.
- **Random arm (no-case W and V):** 8/12 samples produced both documents (4 stopped before the verdict); 6/8 chose X1's
  gold. With the schema as is, the reasoning document after not_governed needs a `case_approach` (filled with a fixed
  sentence for now; a format decision).
- **Luna writing is reliable:** 24/24 targets passed the full structure check on the first try, every arm, including
  revised (K and verdict from C′) and transfer (aligner fact maps).

## Commands

    PYTHONPATH=code .venv/bin/python -m pipeline.sft.wexp sample     --run results/sft/wexp1 --per-arm 3
    PYTHONPATH=code .venv/bin/python -m pipeline.sft.wexp write      --run results/sft/wexp1
    PYTHONPATH=code .venv/bin/python -m pipeline.sft.wexp granite    --run results/sft/wexp1 --k 8 --workers 8
    PYTHONPATH=code .venv/bin/python -m pipeline.sft.wexp restate    --run results/sft/wexp1 --workers 8
    PYTHONPATH=code .venv/bin/python -m pipeline.sft.wexp likelihood --run results/sft/wexp1 --workers 4
    PYTHONPATH=code .venv/bin/python -m pipeline.sft.wexp guided     --run results/sft/wexp1 --k 2 --workers 8
    PYTHONPATH=code .venv/bin/python -m pipeline.sft.wexp report     --run results/sft/wexp1

Code: `code/pipeline/sft/{pairgold,targets,wexp}.py`, `code/pipeline/sft/prompts/writer.v1.md`; roles `sft_aligner`,
`sft_writer`, `sft_restater` in `config/models.yaml`.

## LLMs in the loop

- GPT-6 Luna on Bedrock: aligner (`sft_aligner`, T 0), writer (`sft_writer`, T 0.3, reasoning high). Bedrock usage is
  not metered in provenance (known gap); 24 writes + ~45 aligner calls.
- Base Granite 4.2 8B on local vLLM: restater (chat, thinking off, T 0.7), G and G+notes (raw completions, mode B,
  T 1.0 policy settings), no-case W/V, likelihood scoring.
- TypeSafe Jev 1.14 (OpenRouter): the two gates.
- Claude-read: the qualitative judgments above (case_approach as directive in ~11/15 G samples; G+notes cites the
  decisive condition and fired flip item in the two cells read side by side). Not a systematic rating.
