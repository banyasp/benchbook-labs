# Cross-domain transfer pairs: plan (draft for Peter, 2026-11-09)

**Thesis being tested.** The value of Benchbook is not RAG (a relevant case about the same thing helps). It is
analogy through the considerations: a case from a different national-security manifestation that implicates the same
equities in the same way should help, where surface similarity would not. Sisters stay inside national security
(Peter, 2026-11-09): the equity registry is a national-security one, so going outside it changes the equities.

**Design (Peter, 2026-11-09).** Keep the live trace T(X1); build only the case X2. Traces are expensive and carry the
leak risk; a case card is rendered by code.

## The pair generator: X1 → X2

| step | what | who |
|---|---|---|
| 1. K skeleton | From X1: each consideration's equity, favors (mapped to option roles), weight, decisive flag; the core tension in one sentence. No `why` text carried over (some restate the verdict). | code |
| 2. Plan | Pick a different national-security sub-domain and a situation whose facts would carry each consideration; map the options one to one; say which facts carry which consideration. | strong model (GPT-6 Luna now; a Claude model on Bedrock if its access is enabled) |
| 3. Write X2 | Full scenario: frame, facts, options, considerations (same equity ids), reasoning, verdict = the option mapped from X1's verdict; flip conditions, lesson, limits. Lineage `{parent: X1, operator: transfer, detail: sub-domain + the K map}`. | GPT-6 Luna |
| 4. Checks | (a) blind re-extraction of K2 from X2's facts and frame by a second call, diffed against K1 (equity, direction, weight); (b) answer-leak check (frame, facts); (c) "what does this setting add?" probe for strong considerations K1 lacks; (d) cold solve of X2 without the answer: must reach the mapped verdict; (e) technique screen. Any failure: one repair round, then drop. | GPT-6 Luna + code |
| 5. Store | `data/store/scenarios/<X1 family>/DR-…-transfer<k>@v1.yaml`, tagged `transfer`; a readable log of every pair (anchor, sister, sub-domains, K map, check results). | code |

Optional variant (Peter's first design): a target change in considerations ΔK on the transferred case, giving a
sister whose verdict should flip; tests that the model distinguishes rather than copies.

## The experiment

Same trace T(X1), different cards, base Granite, scored against X1's answer key exactly as in the all-pairs grid
(`eval/allpairs.py` machinery: control k=8, verdict via the tuned option translator, all scores and judge matrices
kept):

| arm | card | expectation if analogy works |
|---|---|---|
| none | — | baseline (B2 gives this already for 64 X1s) |
| transfer | C(X2), same K, other sub-domain | above none |
| decoy | C(X3), a case from another sub-domain with different K | about none (or below) |
| self | C(X1) | ceiling |
| transfer-flip (optional) | C(X2′), ΔK so its verdict differs | model distinguishes: does not copy X2′'s verdict |

k samples per cell (8), so each X1 has a per-arm success rate rather than a single 0/1. Headline: transfer − none and
transfer − decoy, with family-bootstrap CIs; secondary F/Q/K metrics show where the case helps.

## Sizing

X1 = the clean corpus traces already rendered (B2's 64 + C1/D1's 190), 2 sisters each → about 500 X2. Generation +
checks: GPT-6 Luna on Bedrock, cents per sister. GPU: (none 8 + transfer 2×8 + decoy 8 + self 8) × 254 ≈ 10,000
replies ≈ 3 days at 150/hour; start with 60 X1 (≈ 1 day).

## Open questions for Peter

1. Which sub-domain list to draw sisters from (a fixed list of about 12 national-security manifestations?).
2. Include the transfer-flip arm in the first run, or after?
3. Enable a Claude model on Bedrock for the planning step (the instance role cannot invoke it today), or stay with
   GPT-6 Luna for both steps?
