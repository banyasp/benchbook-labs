You are writing the REVISED CARD for one reference case in the Benchbook MVP, data spec v2.6. The revised-card control shows that an agent actually uses the card it is served: the scenario is unchanged, but the card's weighing is different, so on the same facts the right answer is different. The spec and template below are authoritative; a script will validate your file and send you its error list if it fails.

# The spec (verbatim sections)

{SPEC}

# The template (verbatim)

{TEMPLATES}

# A worked example of a reference case and its revised card

Reference:

{EXAMPLE_REFERENCE}

Its revised card:

{EXAMPLE_REVISED}

# Balance rules (the options must stay exactly as they are in the reference, so they already obey these)

{BALANCE_RULES}

# Scope

{SCOPE_RULES}

# The reference case you are revising

{REFERENCE}

# The seed

{SEED}

# Your assignment

{ASSIGNMENT}

# What to write

One file, the revised card, a complete reference case in the same form as the reference:

- `id` is `<CASE>-rN` as the assignment gives it; `title` is the reference's title plus " (revised)"; `status: draft`; `version: 1`.
- `scenario` is copied from the reference WORD FOR WORD: every field, the situation, the question and all options with their `move`, `to`, `irreversible` and `do` text. A script compares it with the reference after loading both and rejects any difference.
- Only the weighing changes, and with it the answer for this scenario. Change the weight of the consideration(s) the new answer rests on, `choice` (it must differ from the reference's), `basis`, `decisive`, and rewrite `judgment`, `lesson`, `limits` and `boundaries` so they are consistent with the new weighing. Keep every consideration's `fact` word for word; keep `id`s. `would_change` items must differ from the new choice; `would_not_change` has 1-2 items. `tempting_wrong.option` must not be the new choice. Obey the judgment guide lengths.
- `provenance.drafted_by: "{MODEL}"` exactly. `provenance.caveats` must say the card is illustrative, not Peter's view, written only to test that an agent uses the card it is served, and that the reference remains the real case. Keep the reference's caveats about invented figures.
- The revised weighing is an illustrative rival view and need not be the right answer, but it must be coherent: if the new choice hands the call up, `judgment.handoff` states plainly the reason the revised card gives for doing so.

Output only the file content in one fenced block.
