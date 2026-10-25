# Smoke test, 2026-10-25: untrained Granite 4.2 8B, one B001 trace, PDF step format

**Input.** `INT-301-v01` (restyle, gold **B** = refer to the Provost Marshal, relation `follows`), served the right
card `INT-301.reference.yaml` rendered by `mvp.card` (v2.6 format: no case fact ids, options A-C). Trace flattened
with `mvp.trace_text` into one user message after the trace's system prompt. The benchbook injection carries a
smoke-only equities list (the card's 4 values + 2 unused, glosses mine) and a field skeleton of the PDF's steps
(pp. 14-18, plus `via`), no worked example. Prompt: 3,793 tokens. `temperature=1.0, top_p=0.95, seed=0`, one sample
per mode. Files: `INT-301-v01.prompt.json` (messages), `.prompt.rendered.txt` (after the chat template),
`.think.*` / `.nothink.*` (reply YAML + full JSON incl. the thinking text).

| | thinking | non-thinking |
|---|---|---|
| tokens / time | 9,014 (≈7.5K of it thinking) / 234 s | 2,383 / 60 s |
| 7 steps present, in order | yes | yes |
| parses as YAML | all 7 | 3 of 7 (copied my `<case id>` placeholder literally: `case: <case id: CASE INT-301>`) |
| choice | LIVE-O1 = refer = **B, correct** | LIVE-O1 = refer = **B, correct** |
| relation | follows, correct | follows, correct |
| options enumerated | 2 (dropped the hand-up, C) | 3, all |

**Distance from the format (thinking reply).**
- Case-side ids: the v2.6 card has no case fact ids, so fact mapping names case facts in free text and invents
  `CASE-O1/O2` for options (non-thinking used `INT-301-A/B/C`). Expected (reconciliation D1); the converted cards fix it.
- Fact mapping: no `case:` key; every frame item `same` (gold is a restyle, so `same_kind` is arguable); puts
  considerations (`c2, c5`) in fact `case_only`.
- Consideration mapping: no `role`; maps c4 and c3, lists c2 and c5 as case-only. **It never engages c5, the bar
  that decides the case**; it decides on c4 alone. Only 2 live considerations and 4 facts: thin.
- Applicability: `frame` filled with prose instead of same/same_kind/different.
- Verdict: `now` lists ids, not actions; `flip_conditions` is a flat list, not would_change / would_not_change /
  watch_for; flip1 sends a foreign tie to O2 (filing). The card says a confirmed tie → A, a suspected one → C, which
  it can't express without option C.

**Takeaways.** The model follows the step structure from a schema alone, and both modes get the decision right on
this one easy restyle trace (n=1, temperature 1: no accuracy claim). The gaps are in the mapping fields, which are
what the reasoning scorers grade. Non-thinking is ~4x cheaper and enumerated better here; whether to run Checkpoint 2
with thinking on is a decision for Peter. The parser in 2a should tolerate the `<…>` placeholder slip, and the format
prompt should use concrete examples rather than angle-bracket placeholders.

**Shortcut cues seen.** (1) The thinking reply dropped the hand-up option entirely, so on this trace "the options it
enumerates" is not the scenario's option set; option enumeration needs its own score before choice accuracy means
much. (2) The live scenario's options aren't in the trace; the model writes them, so LIVE-O ids are in the model's
own order. Translating them to gold needs the fact/option alignment step, not position.
