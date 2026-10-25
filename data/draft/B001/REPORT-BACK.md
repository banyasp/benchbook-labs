
### 2026-10-01 · data generation session: conformance and batch B001

**What the pipeline changed to conform**

| §8 row | Now |
|---|---|
| ~200-word exemplars, ≤ 6 factors, up to 3 served | Reference cases per §2 (simple form, `c1…` ids, `favors` lists, judgment prose, card ≤ ~1,000 words). One card per decision, injected by the harness. |
| 1.5–4k-token scenarios, 5–9 documents, decisive-share curriculum | Live specs per §3 rendered as §4 traces: 500–1,200 words before the card, decisive share 10–25%, documents as tool results. The curriculum is retired. |
| YAML scenario or option menu shown to the agent; consult tool | Chat trace with no menu, ending with the exact harness injection; no consult tool. |
| Catalog-wide factor ids; `solver_v2_1` on catalog factors | Case-local `c1…` ids; the 28 values are the only shared vocabulary. The solver is kept only as an optional per-value second check and was not run on B001. |
| Letter-coded ids, single `favors`, separate time field | Neutral ids, `favors` lists, time folded into the consideration whose value imposes it. |
| Answer-letter scoring | Strict signature matching through `mvp.py reply-score`, for the right-card, revised-card and decoy arms. |
| Mapping with `decide.choice` and live letters | Mapping v2.5 in trace mode plus tool calls. |
| ≤ 30-token tag quotes | `facts` in the trace (quote, message index, planted index). |
| Escalation as the safe default | Autonomy by default. Each batch plan sets the hand-up share up front; a hand-up gold needs a lack of authority. |

New code in `benchbook-labs/code/datagen/`:
- `check_batch.py` runs §11 steps 1–4 on every arm. It also makes the checks `mvp.py` leaves to the pipeline:
  - revised-card coverage, with the scenario identical word for word to the reference's;
  - served-card files present in each folder;
  - words and fact share outside their bands treated as errors;
  - a leak scan, including "golden" and "partially";
  - `floors` on the batch and on the cumulative set;
  - the shares of gold letters, hand-up golds, irreversible golds and longest-option golds, and the variant mix;
  - PROPOSED LABEL present on `novel` and `cross` items;
  - two shortcut checks taken from the training handoff (risks 1 and 2): the share of lives whose gold follows the card (the copy-the-card baseline), and a "most specific signature" floor.
- `llm.py` and `run_stage.py` handle drafting. Stages run reference → revised → live → render → reply → critic, with at most two repair rounds against `mvp.py`.
- Each stage prompt embeds the spec sections verbatim, plus the templates and the AUT-001, INT-103 and AGT-201 examples.
- Training-bound stages accept only allowlisted open-weight families (gpt-oss, Gemma 4, Mistral, Olmo). They refuse Claude and closed GPT models.
- The critic must come from a different family than the drafter. Every call is logged to `provenance.jsonl`.

Batches go in `benchbook-labs/data/draft/<batch>/`.

**Batch B001: checklist results (run on the Mac copy with your `mvp.py`)**

B001 contains three case families, each built from a real public seed:
- INT-301: DAIG Intelligence Oversight Guide, App. F;
- REL-301: CDSE GS160, Lesson 8;
- OVS-301: USNA ELJO, "Need to Know".

Each family has a reference card, a revised card (`-r1`) and four lives (restyle, trap and two flips). That makes 12 traces and 30 gold replies (12 right-card, 12 decoy, 6 revised-card).

1. `validate`: 21 of 21 YAML files OK with no warnings. Card length is 987, 989 and 997 words.
2. `floors`:
   - The batch (15 decisions, chance 0.306) flags nothing. Its highest scores are always B, most clauses and never irreversible, each at 0.333.
   - The cumulative set with examples-v21 (48 decisions, chance 0.288) is still flagged on never irreversible (0.417), longest (0.396) and most clauses (0.542). These flags come from the 13 examples, per §7. Hand-up now passes, at 0.312.
3. `trace-check`: 12 of 12 OK. The traces run 684–873 words, with fact share 0.124–0.189.
4. `reply-score`: 30 of 30 have gate 1 and acted equal to the expected option. Relation and fit are 1.0, and so are differences wherever they are scored. Totals:
   - right card 1.888–1.893;
   - revised card 1.593;
   - decoy 1.588–1.593.
5. `trace-view`: all 12 `.trace.md` files were written. I spot-read one trace per family and found no menu, no leaks and no highlighted facts.
6. Nothing was dropped or relabeled. Two fixes were made before acceptance:
   - The v04 flips first landed on options that were also the longest, because the length roles collided with the flip. I reworded those options.
   - The decoy arm was added.

Gold mix: A 5, B 5, C 2, D 3. Hand-up golds 2 of 15 (both for lack of authority), irreversible golds 4 of 15, longest-option golds 0 of 15.
Copying the card would get 6 of 12 lives right (50%). Picking the option with the most specific signature scores 0.29, below chance (0.31): the gold option is uniquely the most specific in 2 of 12 lives and tied in 3.

**Cannot meet, and questions for Peter**

1. **Authorship.** Claude drafted B001, because this session can reach no open-weight endpoint: there is no OpenRouter key, and the container's AWS credentials belong to the sandbox, not to you. So B001 is prototype and evaluation material only (§10). To generate training data, the pipeline needs one of the following. Which do you prefer?
   - `OPENROUTER_API_KEY`;
   - an AWS profile with Bedrock access, set as `BENCHBOOK_AWS_PROFILE` and `BENCHBOOK_AWS_REGION`;
   - running `code/datagen` on your Mac.
2. **Restyle maximum.** §3.1 has a restyle list every consideration as `here: same`. That makes `planted` non-empty, so differences are scored and the maximum is 1.9, not the 1.6 that §5 states. AUT-001-v01 does the same. Which is intended? Until you rule, the checker accepts 1.9 for a restyle that lists `here: same`.
3. **Novel and cross variants.** B001 has none, because their labels are PROPOSED and cost your time. How many per batch?
4. **Strict-matching misses** the drafters found. These stay wrong for now:
   - INT-301: a referral to CID alone, without the Provost Marshal;
   - OVS-301: a report sent as an attachment with no message, or a private word to the poster without closing the moderation flag.
5. **Seed readings to confirm:**
   - INT-301: the trap's "wholly open source" wording;
   - REL-301: GS160 request 5 read as denied rather than referred;
   - OVS-301: `usp_privacy` used for Privacy Act records.
