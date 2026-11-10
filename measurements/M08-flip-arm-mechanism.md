# M08 · Flip arm mechanics: relation, via, mapping buckets, contamination

**Status: COMPLETE** on the full pilot-2 data (M06 Luna and M07 Granite mode C). Computed 2026-11-10. The same measures
for mode A are in M09.

## What was measured
- **Question.** On the flip arm, does the model use the flipped case's reversed `would_change` condition, or copy its
  verdict? Does it rewrite its own reading of the live facts to match the case?
- **Flip structure.** What a flip case actually changes compared with its sister.
- **Population.** All flip-arm replies of M06 and M07: 216 each, 27 flip cells, of which 20 X1s have flip cells. The
  bucket measures use the 30 accepted batch-2 flips.

## What was observed

**What a flip changes** (the 30 accepted batch-2 flips, against their unflipped sister):
- Every flip changed at least one consideration's `favors` or weight; 26 of 30 changed the decisive set.
- The reversed `would_change` item is prose in the sister's domain and cites no fact or consideration id (0 of 30).

**Relations declared on the flip arm** (from the reply's `verdict.relation`):

| | follows | flips | distinguished | not_governed | none |
|---|---|---|---|---|---|
| Granite (C) | 56% | 3% | 31% | 3% | 7% |
| Luna | 12% | 52% | 34% | 2% | 0% |

On the decoy arm, Luna says `not_governed` 97% of the time; Granite says `follows` 37%, `distinguished` 42% and
`not_governed` 12%.

**Use of the flip condition and mapping:**

| Measure | Granite (C) | Luna |
|---|---|---|
| Declares `flips` and `via` names the case's would_change | 3% | 52% |
| Flipped consideration mapped as "corresponding" (correct: same equity, other direction) | 36% | 88% |
| … mapped as "matched" (claims it is the same) | 27% | 1% |
| … listed as case_only | 22% | 9% |
| … not mentioned | 15% | 2% |
| Reasoning or applicability mentions a flip condition | 18% | 45% |

**Contamination.** The share of the model's own enumerated considerations (step 3, written before any mapping) whose
`favors` includes the flipped case's verdict option, which is never X1's gold. Mean over X1, counted on X1s that have a
flip cell. The no-case arm is the baseline.

| Arm | Granite (C) | Luna |
|---|---|---|
| no case | 36% | 24% |
| own case | 19% | 14% |
| transferred sister | 23% | 18% |
| flipped sister | 50% | 22% |
| other anchor's sister | 31% | 18% |

**Granite's flip-arm cross-tabs (Claude-read / ad-hoc, 2026-11-10):**
- Accuracy is 26% even when Granite maps the changed consideration as corresponding.
- When it declares "distinguished", it still takes the case's verdict 21 of 55 times (21 correct, 13 off-menu).
- Its flip replies average about 7,900 completion tokens, so the token budget is not the constraint.

## How
- **Code.** `PYTHONPATH=code .venv/bin/python -m eval.analysis.mode_compare --runs pilot2 pilot2-luna --out results/transfer/MODE-COMPARE-pilot2-granite-C-vs-luna-full-20261110.md`
  (`code/eval/analysis/mode_compare.py`). It is deterministic, with no LLM.
  - It re-parses each raw reply with `bench.schema.parse_reply`.
  - It loads the flip structure from `results/transfer/build-batch2-20261109.jsonl` (`flip_info`: the changed fact
    ids, the changed consideration ids and the would_change ids).
  - It finds the bucket of `REF1-<consideration id>` in the reply's `consideration_mapping`.
  - It matches the flip-condition mention with a regex over the reasoning and applicability.
  - Contamination maps the reply's own option ids to X1's options through the judge's stored
    `option_alignment.translation` (in `details/*.json`). That translation comes from the Jev judge (an LLM) at
    scoring time.
- **Older script.** `code/eval/analysis/flip_relation_audit.py` (earlier version, same counts).
- **Ad-hoc parts.** The cross-tabs and the first contamination numbers (O19: 32/19/45 on 859 interim samples) were
  ad-hoc queries; the table above supersedes them.
- **LLMs.**
  - Policy replies and Jev option translation are inherited from M06 and M07.
  - Claude-read: the description of the would_change items (prose, awkward negations) and the cross-tabs.

## Key observations
- **Luna reads the flip condition.** It maps the changed consideration as corresponding, declares `flips` with the
  right `via`, and its own considerations stay unbiased (24% → 22%).
- **Granite rarely declares `flips`.** It often calls the changed consideration "matched", and its own considerations
  shift toward the case's verdict (36% → 50%) before any mapping step. That is the "reinterpret my considerations to fit
  the case" disposition Peter described, measured directly.
- Interpretation: `docs/OBSERVATIONS.md` O19.
