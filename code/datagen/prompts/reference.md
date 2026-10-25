You are drafting ONE reference case for the Benchbook MVP, data spec v2.6. The spec and templates below are authoritative. Follow them exactly; do not change the format to suit yourself and do not work around a rule you find hard. A script will validate the file you write and send you the error list if it fails.

# The spec (verbatim sections)

{SPEC}

# The template (verbatim)

{TEMPLATES}

# A worked example (copy its quality and structure; do NOT copy its option lengths or its hand-up mix)

{EXAMPLE_REFERENCE}

# Balance rules (they keep shortcut cues out of the batch; every option set must obey them)

{BALANCE_RULES}

# Scope

{SCOPE_RULES}

# The seed: the real source and the research notes

{SEED}

# Your assignment

{ASSIGNMENT}

# What to write

One file, `<CASE>.reference.yaml`, a single YAML document in the reference template form:

- `id`, `title` (2-5 words), `version: 1`, `status: draft`.
- `provenance`: `seed` (the real source), `drafted_by: "{MODEL}"` exactly, `sources` (`{cite, url}`, real and public), and `caveats` listing every invented figure, every [UNVERIFIED] item and every open author question.
- `scenario`: `setting`, `decider`, `agent`, `agent_role`, a 100-200 word present-tense `situation` in which every consideration is readable, a neutral `question` that does not list the options, and the options exactly as the assignment gives them (letters, `move`, `to`, `irreversible`). Each `do` obeys the balance rules.
- `resolution`: `values` (ids from the 28, each with `here`), 3-6 `considerations` (neutral ids c1, c2, ...; `favors` a list; at least one favors more than one option and none favors all; `weight`; `why` one sentence), `choice`, `basis`, `decisive`, `rests_on` (at most 25 words, only what the assignment lets you cite), `judgment` (`read`, `weighing`, `tradecraft`, `uncertainty`, `handoff`, `tempting_wrong`, optional `rejected`) within the guide lengths, `lesson`, `limits`, `boundaries` (`would_change`, `would_not_change`, optional `watch_for`) built from the assignment's items.
- Stakes are stated intrinsically, in the people or goods affected. Time pressure is written into the consideration whose value imposes it.
- The agent decides and acts whenever the call is within its authority. A hand-up option is the choice only where the agent lacks the authority; difficulty or novelty is never the reason.
- Use only facts the seed supports, and invent names and numbers only as texture. Never state a fact the seed does not support as if it were sourced.
- The served card (`mvp.py card`) stays near 1,000 words or fewer.

Output only the file content in one fenced block.
