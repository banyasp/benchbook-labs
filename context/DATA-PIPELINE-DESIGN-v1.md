# Benchbook data pipeline — design v1 (draft for discussion, 2026-10-25)

*Drafted with Claude in Peter's claude.ai session. Ground truth for formats is the Research Plan v0.4 PDF; this
doc designs how data gets from the open web into the representations the PDF needs. Everything here is a
proposal until Peter rules on it. Keep every version.*

## 1. The core idea: one canonical record, many projections

SFT targets, RLVR answer keys, eval samples and library entries are **views of the same information**. If each is
written separately they drift. So the pipeline stores a small number of canonical objects and **projects**
every downstream representation from them with deterministic code.

| Canonical object | What it is | Owns |
|---|---|---|
| **Source** | One raw document, immutable, content-addressed | bytes, fetch metadata, license |
| **Span** | A located piece of a Source | `doc_sha#page.para[char_start:char_end]` |
| **Decision Record (DR)** | One decision under tension, structured: setting, decider, agent role, question, options, facts, considerations, verdict, reasoning, flip conditions | global ids for every fact / consideration / option; evidence span(s) or `synthesized_by` on every field |
| **Equity registry** | Controlled vocabulary of equities (id, gloss), plus per-deployment equity sets | the shared ids that make consideration-level matching and cross-domain transfer possible |
| **Deployment profile** | The agent's world: role, tools, standing orders, delegations, people, noise generators | everything a trace's system prompt and tool calls are built from |
| **Lineage edge** | `live DR ← operator(params) ← case DR` | the perturbation that produced a live scenario, and its **delta** (which facts / considerations were added, removed, revised, and how) |
| **Pairing (gold analogy)** | One (live DR, served case DR) pair and the gold correspondence between them | fact mapping, consideration mapping, applicability, relation, `via`, verdict choice — all in global ids |
| **Trace** | A rendered agent context for a live DR | messages + a **span map**: where each live fact appears in the trace |

**Projections (pure functions, regenerated whenever an input changes):**

- **Served case** = DR → PDF case format, ids renumbered `REF1-F1…`, `library` block stripped. The renumbering
  table is kept so answer keys can translate back.
- **SFT example** = (Trace, Equities, Served case) as masked prompt + **golden reasoning** as target (PDF's 7
  generated steps, `kind:` documents, with live ids `LIVE-F*` numbered in trace order from the span map).
- **RLVR answer key** = Pairing + gold live facts (+ weights: facts behind decisive considerations ×2) + allowed
  noise facts (true, rendered, not needed) + frame gold + flip ids + options map, all in served-id space.
  No prose (reasoning and applicability-why are never scored).
- **Eval sample** (Inspect) = same prompt as SFT for each arm of the PDF grid + answer key + distance features.
- **Library entry** = DR + index rows (section 4).

SFT golden reasoning and the answer key now come from the **same Pairing**, so they cannot disagree. The only
thing SFT has that the key lacks is prose, and the only thing the key has that SFT lacks is weights and the
allowed list.

## 2. What else the experiment needs (beyond SFT, RLVR, harness)

1. **Equity registry** — versioned. Map the v2.6 schema's 28 `value` ids onto it. Without shared ids,
   consideration-level retrieval and the transfer tests don't work.
2. **Deployment profiles** — traces need a world (tools, orders, delegations). Reuse across many scenarios.
3. **Lineage / perturbation graph** — gives gold labels *by construction*, the eval x-axis (distance by the PDF's
   perturbation axes), and leakage control.
4. **Splits fixed up front, at the family level** — a case and all its variants (and a whole held-out domain)
   are assigned to train / dev / test *before* generation, so nothing leaks.
5. **Controls as first-class records** — revised ("augmented") cards, near-miss and far decoys, transfer
   variants. They are DRs with lineage, not special files.
6. **Provenance and authorship** — every field records source span or generating model + prompt version. The
   training-bound rule (allowlisted open-weight models only) is enforced from this metadata.
7. **Review state** — `candidate → extracted → verified → reviewed → approved → retired`, with Peter's sign-off on
   holdings sampled to fit his ≤5 h budget (the existing Review Desk).
8. **Shortcut statistics** as a gate — option position, option length, hand-up share, irreversible share, number
   of supporting facts vs gold, relation mix per similarity band (the existing `floors` checks, extended).
9. **Classification marking** on cases (PDF: compartmentalization) — one cheap field now; the harness filters on
   it later.
10. Later, not MVP: monitor-trigger labels (where in a trace a consequential decision begins), retention and
    safety benchmark sets (IFEval, MMLU-Pro, BFCL, AgentDojo, StrongREJECT, XSTest, AgentHarm — the PDF's list).

## 3. Pipeline stages

Mapped onto the PDF's data-generation figure (raw material → fetch → quality corpus → extract → scenario:judgment
→ augmenter → perturbed scenarios → trace generator / LLM decider / eval extractor, with the A/B test).

| # | Stage | In → Out | How | Gate (fails stop the item, not the run) |
|---|---|---|---|---|
| S0 | Source registry | catalog → `sources.yaml` | start from `context/sources/source-catalog.csv` (150 sources, license and fit columns) | public + license recorded |
| S1 | Acquire | URL → raw blob | fetch (or manual drop for sites tools can't reach); store bytes at `raw/<sha256>`; record URL, time, headers, license | sha recorded; never modified again |
| S2 | Normalize | blob → Document | PDF/HTML → text with structure (pages, headings, paragraphs), OCR if needed; every paragraph gets a stable **span id** | text extracted; span ids stable across re-runs |
| S3 | Segment & triage | Document → Episode candidates | LLM pass finds decision episodes (a decider, options, a tension, ideally an outcome and stated reasons); scores clarity, reasoning present, relevance, safety scope; clusters duplicates of one incident across sources | score ≥ threshold; in safety scope (decision ethics, law, policy — no weapons employment, targeting, intrusion or collection technique) |
| S4 | Extract | Episode → **DR** | LLM structured extraction in the PDF case format; **every fact and consideration cites span ids**; anything not in the source (options the source didn't list, counterfactual flip conditions) is marked `synthesized_by` | schema valid; equities from registry |
| S5 | Verify | DR → verified DR | grounding check: an independent judge confirms each cited span supports its fact (entailment); consistency (verdict rests on its decisive considerations; flip `then:` targets exist); no leaked option labels | grounding ≥ threshold; failures go back to S4 once, then to review |
| S6 | Review & promote | verified DR → **Case** | Peter rules on sampled holdings in the Review Desk; approved DRs become library cases (versioned) | `approved` |
| S7 | Perturb (augmenter) | Case → live DRs + lineage + delta | operators on the case's skeleton, each with a known gold effect (table below) | the operator's precondition holds; gold set by construction |
| S8 | Render trace | live DR + deployment profile (+ raw corpus for texture) → Trace + span map | LLM trace generator; decisive facts 10–25% of words, never highlighted or last; noise from the profile and from real source material | words 500–1,200; every gold fact locatable via the span map; leak scan clean |
| S9 | Decide & pair | (live DR, case) → Pairing | **two routes that must agree**: (a) by construction from the S7 delta; (b) an independent LLM Decider given both DRs (structured, not trace) writes mapping + verdict. Disagreement → review | routes agree on relation, choice, decisive, mapping buckets |
| S10 | A/B trace test | Trace vs DR | a model decides from (trace, case) and from (live DR, case); if the answers differ, the trace lost decision-relevant information | decisions match (PDF's A/B test) |
| S11 | Project | Pairing + Trace + Case → SFT / answer key / eval samples | deterministic code; golden reasoning prose from the base model, label-conditioned and filtered by the scorers (PDF) | format verifier + scorers pass |
| S12 | Assemble | all → datasets | splits by family/domain (fixed at S6), balance floors, shortcut stats, exports: HF datasets (TRL SFT with loss masks; GRPO prompts + gold JSON), Inspect samples | floors pass; no family crosses splits |

**Perturbation operators (S7)** — the PDF's axes plus the scenario families already designed:

| Operator | Change | Gold relation | Delta recorded (= gold mapping) |
|---|---|---|---|
| restyle | surface only | follows | all facts `matched` (reworded), considerations `matched` |
| revise fact (non-dispositive) / trap | apply a `would_not_change` item | follows | that fact `corresponding`, its consideration `matched` |
| a fortiori | strengthen the winning side | follows | fact `corresponding`, consideration `corresponding` (weight up) |
| flip (minimal pair) | apply one `would_change` item | flips, `via` that item | fact(s) `corresponding`/`case_only`/`live_only`, consideration changed; choice = item's `then:` |
| add fact | a new live-only fact | follows or distinguished (author-labeled if it decides) | `live_only` fact; de-novo consideration if it implicates an equity |
| remove fact | drop a case fact | follows, or flips if decisive | `case_only` |
| inter-fact influence | change how two facts interact | author-labeled | — |
| option set | add / remove / reshape an option | by construction where the options map is clear | options map |
| authority / role | change who decides or the agent's role | often flips toward hand-up; author-labeled | frame `role` / `decider` changes |
| domain transfer | re-instantiate the case's skeleton in another domain | follows, or flips with a `would_change` analog | all facts `live_only`/`case_only`; considerations `matched` by role |
| near-miss decoy | same surface facts, different equities at stake | not_governed | facts mostly `matched`, decisive considerations `case_only` |
| far decoy | unrelated case served | not_governed | — |
| revised card (augmented case) | edit the case's weighing, not the scenario | follows the revised card | — |

The **distance** of a live scenario from its case is a function of its lineage: which operators, how many facts
touched, and their magnitude (weights per axis: Peter). Decoys and transfers sit at the far end.

## 4. Library storage and retrieval by consideration structure

**Store:** one YAML file per case version in git (human-readable, diffable) + an **index database** rebuilt from
the files (SQLite or DuckDB to start; Postgres + pgvector if it grows). Raw sources stay in a content-addressed
store (local `data/raw/`, or S3) with cases pointing at spans.

**Index tables:** `cases` (id, version, domain, decider type, agent_role, classification, status, split),
`options` (case, id, abstract move: act / partial / ask / refuse; irreversible; reveals_asset?),
`facts` (case, id, kind, status, span refs), `considerations` (case, id, equity, favors→abstract moves,
weight, decisive, pulls toward or against the choice), `flip_conditions` (case, id, then, equity touched),
`equities`, `embeddings` (situation, question, each consideration's `why`).

**The structural signature of a case** — what retrieval matches on, abstracted away from domain facts:
- the **tension**: the equities on each side of the choice, with weights (e.g. civilian_life·strong vs
  mission_effect·weak + source_protection·weak);
- the **decisive** consideration(s) and the conditions their priority depends on (from the reasoning and
  `would_change`);
- the **move structure** of the options (act-revealing vs covert hand-off vs hold) and which one won;
- the **authority shape**: agent role, decider, delegation (acts on own authority / must hand up).

**Retrieval (hybrid):** filter (classification, deployment's equity set, agent role) → **structural score**
(weighted bipartite matching between the query's consideration set and each case's, on equity + polarity +
weight, decisive matches counting double; plus tension, move-structure and authority match) → semantic rerank
(embeddings) as tiebreaker only. Facts never drive retrieval; that is what lets the drone-boat case reach the
journalist scenario.

**The chicken-and-egg problem.** The agent enumerates considerations only *after* the case is injected, but
retrieval needs considerations *before*. So the harness needs a **query extractor**: a separate, cheap model call
that reads the trace at the trigger and emits a provisional signature (equities at stake, tension, move
structure, role). For the MVP experiment, retrieval is the **oracle** (serve the designated case), so this only
matters for the library-size experiment and deployment — but the index should be built for it now.

**Bonus:** the same structural signature gives coverage analytics for Peter's online-alignment idea — the density
of library cases vs observed deployment scenarios in signature space, and where the gaps are.

## 5. Ids, versions and reproducibility

- Global ids: `src:<sha12>`, spans `src:<sha12>#p3.4`, DRs `DR-<family>-<n>@v<k>`, facts `…/F<n>`,
  considerations `…/C<n>`, options `…/O<n>`.
- Served/rendered views renumber (`REF1-F1`, `LIVE-F1` in trace order); the renumbering tables are stored with
  the projection, so a scorer can always translate back to global ids.
- Every derived artifact records its inputs' hashes, stage version, model id and prompt version. Stages are
  re-run make-style when an input hash changes; outputs are cached by content hash.
- Raw is immutable. Derived records are versioned, never overwritten (`versions/`).

## 6. Storage layout (proposal)

```
data/
  raw/<sha256>                 immutable source bytes (+ .meta.json)
  docs/<sha12>.jsonl           normalized text with span ids
  episodes/                    candidates with scores
  records/<family>/            DRs (cases, live variants, controls) + lineage.yaml
  registry/                    equities.yaml, deployments/*.yaml, splits.yaml
  traces/<family>/             rendered traces + span maps
  pairings/<family>/           gold pairings (both routes + agreement)
  exports/<version>/           sft/, rl/, eval/  (projections; regenerable)
library/                       served cases + index.sqlite (rebuilt from records/)
```

## 7. Questions for Peter

1. **First sources.** Start from the 150-source catalog, the Hard Calls research strands, or both? Which 2–3
   domains first, and which domain is held out?
2. **Golden reasoning author.** The PDF says the base model writes it (label-conditioned, filtered). If Granite's
   prose is weak, may an allowlisted larger open-weight model (e.g. gpt-oss-120b) write it instead?
3. **Distance weights** across the perturbation axes.
4. **Review budget.** Where should your ≤5 h go: holdings (S6), label disagreements (S9), or transfer
   faithfulness checks?
5. **Equity registry.** Adopt the 28 values as the equity list, or define a shorter deployment-facing list (the
   PDF suggests ~10–20 per deployment)?
