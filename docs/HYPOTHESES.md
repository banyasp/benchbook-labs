# Benchbook — the shape of the problem, assumptions and hypotheses

*Peter Banyas, 2026-10-26 (from his whiteboards; written up with Claude). Peter's figures are authoritative:
`docs/figures/hypotheses-v2-2026-10-26.png` (current) and `docs/figures/hypotheses-v1-2026-10-26.png` (first draft).
Earlier pipeline whiteboards: `docs/figures/*-2026-10-25.png`.*

## The quantities

For a live scenario (trace) T and a library L of cases C, each with a known oracle judgment O(C):

| Symbol | Meaning |
|---|---|
| **O(T)** | The oracle: what the human expert (the deployer's practitioner) would choose for T. Unknown at deployment — the human paid for O(C), not O(T). |
| **C\*** | The most relevant case in L for T. **v1: a single case** (sets of cases are future work). Defined by outcome: C\* = argmin over C in L of ‖O(T) − R\*_C(T)‖. Benchbook search approximates it by structural similarity, because the outcome isn't observable at deployment. |
| **R\*_C\*(T)** | The proxy objective: the best possible extension of the reasoning in O(C\*) to T. Unobservable; estimated with a frontier-model stand-in or by-construction gold. |
| **AR_C\*(T)** | What the model trained for analogical reasoning (SFT + RLVR) decides for T when served C\*. |
| **AR_C(T)** | The same trained model when served whatever case C the harness actually retrieves. |
| **B_C(T)** | The base model when served C (harness only, no training). |
| **B(T)** | The base model alone. |
| **FT_C\*(T)** | A model fine-tuned on C\* (and scenarios derived from it), with C\* *not* served in context (H4). |
| **AR(T)** | Added check: the trained model with *no* case served. |

## The gaps and their levers

| Gap | What it measures | Lever if large |
|---|---|---|
| ‖O(T) − R\*_C\*(T)‖ | How far precedent can take you | Add more relevant cases to the Benchbook, online |
| ‖R\*_C\*(T) − AR_C\*(T)‖ | How well the model extends the best case | Better training (**training objective: → 0**) |
| ‖AR_C\*(T) − AR_C(T)‖ | Cost of serving a worse case than C\* | Better Benchbook search and fetch (**harness objective: C → C\***) |
| ‖AR_C(T) − B_C(T)‖ | Value of analogical training over the harness alone | — (measurement) |
| ‖B_C(T) − B(T)‖ | Value of the harness alone | — (measurement) |

By the triangle inequality, ‖O(T) − AR_C\*(T)‖ ≤ ‖O(T) − R\*_C\*(T)‖ + ‖R\*_C\*(T) − AR_C\*(T)‖: library (approximation)
error plus reasoning (estimation) error. Knowing which term dominates tells a deployer which lever to pull.

## Assumptions

- **A-O1 — Need.** ‖O(T) − B(T)‖ is intolerably high in national-security uses. Stronger, preferred form: it stays
  high for the base model **plus cheap alternatives** (a spec or equities in the prompt, RAG over the cases — the
  PDF's Existing Alternatives). Distance = stakes-weighted verdict disagreement (a wrong irreversible act costs more).
- **A-O2 — The proxy is sound (existential).** ‖O(T) − R\*_C\*(T)‖ is tolerably low. It is really a curve: it grows
  with the distance d(C\*, T), trivially small as C\* → T. The project's claim is that *structural* analogy keeps it
  low over a much larger radius than fact-level similarity (cross-domain transfer). **Testable before any training
  (the H3 pilot below).**

## Hypotheses

- **Main chain.** ‖R\*_C(T) − AR_C(T)‖ < ‖R\*_C(T) − B_C(T)‖ < ‖R\*_C(T) − B(T)‖: training helps beyond the
  harness, and the harness helps beyond the base model.
- **Library.** ‖O(T) − R\*_L(T)‖ falls as the library densifies around T (more, and more diverse, cases). Watch for
  non-monotonicity: a denser library can also bring conflicting precedents from different oracles (register A1).
- **H4 (strengthens the argument; not required).** Analogical reasoning beats fine-tune-and-redeploy:
  ‖O(T) − AR_C\*(T)‖ < ‖O(T) − FT_C\*(T)‖, **especially as d(C\*, T) increases.**
  - Peter's prediction at C\* = T (2026-10-26): the harness **does better than** the fine-tune, and at minimum
    matches it — fine-tuning on one case doesn't guarantee the model recalls and applies it at inference, while
    copying from context is near-perfect. (Measured in v1 by the `self` arm, d = 0.)
  - Possible exception: a fine-tune on C\* plus many derived variants may do well at small-to-middle distances
    (it has learned the neighborhood). That is the strong baseline to beat.
  - Axes: (1) accuracy vs d(C\*, T); (2) **update when O(C) changes** — serve a revised case: the harness follows at
    once, the fine-tune keeps the old behavior until retrained (the revised-card arm measures this); (3) many
    deployers: one model + many libraries vs one fine-tune per deployer, with interference.
  - Include the combination (fine-tune on cases *and* serve them); it is likely the strongest arm.
  - Even if fine-tuning matched on accuracy, the Benchbook wins on the time and cost of updating behavior.
- **Values not baked in.** AR(T) (no case served) should not approach AR_C(T); if it does, training put values
  into the weights (PDF falsifier 2).

## How the data measures each end of the chain

- **By-construction gold** (a flip via a stated condition, a restyle that follows) is a faithful extension of the
  case's own reasoning → it labels **R\*_C(T)**.
- **Source-endorsed gold**, and the independent solve that never sees C → label **O(T)**.
- So derived pairs measure closeness to R\*, natural pairs measure closeness to O, and on pairs with both, the
  disagreement rate between O(T) and R\*_C(T) is a direct estimate of A-O2. Keep the gold tier on every pair.

## H3 pilot — test A-O2 first (proposed, not started)

Cheap, needs no training, and existential: run it before scaling.
1. **Pairs with both oracle answers known:** decisions from one adjudicating body under one set of guidelines
   (DOE OHA security-clearance decisions), especially decisions that cite an earlier decision — there the source
   gives O(C), O(T), and a human judgment that they are linked.
2. **R\* stand-in:** a frontier model on Bedrock (or several, requiring agreement) given C and asked to extend its
   reasoning to T. Also run it *without* C (does the case help at all?).
3. **Measure:** agreement of the stand-in's verdict with O(T), with and without C, by distance band.
4. **Read:** if the stand-in with C rarely reaches O(T), A-O2 fails or the cases' reasoning is too thin; if it
   usually does, the project's premise has evidence before any training.

## Proxy objective vs oracle — Peter's ruling (2026-10-26)

The model should **faithfully carry out the reasoning exhibited in the case** (R\*), not try to guess the oracle
beyond what the case supports. Where faithful extension and the oracle disagree, that is a library gap — rewrite or
add a case — not a training target. Corollary for authors: write reasoning you can stand behind, stating priorities
and how sensitive they are ("would weigh heavily against…"), not rigid if-then rules.

## How the v1 arms measure these (design v2.4 §7.2, 2026-10-27)

| Arm | Measures |
|---|---|
| `relevant` (C = the pair's source case) | AR_C\*(T) for by-construction pairs, where C attains the gold; B_C(T) for the base model |
| `augmented` (case facts altered so its conclusion flips; the PDF's arm) | sensitivity to case facts — the case-side mirror of a flip |
| `revised` (C′: the case's judgment edited, same facts) | H4 axis 2: does behavior follow an updated case at once (minimal pair with `relevant`) |
| `decoy` | the worst-case retrieval error; PDF falsifier 3 |
| `none` | B(T) and AR(T) (values baked in? falsifier 2) |
| `self` (card of T's own scenario) | d = 0 anchor; H4 at C\* = T; ceiling |
| `near_neighbor` | ‖AR_C\* − AR_C‖, the retrieval gap — **v2** (needs the structural index) |
