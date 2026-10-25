You are writing ONE live scenario spec for the Benchbook MVP, data spec v2.6. The live spec is our authoring file: the agent never sees it. A later step renders it into an agent trace, so everything the trace needs (options with signatures, the `render` block, hidden gold) must be in this file. The spec and template below are authoritative. A script will validate your file and send you the error list if it fails.

# The spec (verbatim sections)

{SPEC}

# The template (verbatim)

{TEMPLATES}

# Worked examples (copy their quality and structure; do NOT copy their option lengths or hand-up mix)

A flip variant:

{EXAMPLE_LIVE}

A restyle variant:

{EXAMPLE_LIVE_RESTYLE}

# Balance rules (every option set, reference and live alike)

{BALANCE_RULES}

# Rendering rules (the `render` block and signatures must make a trace that can obey these)

{RENDERING_RULES}

# Scope

{SCOPE_RULES}

# The reference case this scenario is built from

{REFERENCE}

# The seed

{SEED}

# Your assignment

{ASSIGNMENT}

# What to write

One file, `<LIVE>.live.yaml`, a single YAML document. Start with `#` comment lines saying what was built from what, the invented texture, and anything Peter must confirm.

- Top level: `id`, `reference`, `variant`, `boundary`, `revised_cards` (exactly as the assignment lists them; `[]` or omitted if none), `decoys: []` (always empty for now), `scenario`, `render`, `gold`, and `provenance` (`drafted_by: "{MODEL}"` exactly, and `caveats` listing every invented figure and open question).
- `scenario`: same fields as the reference. The options keep the reference's letters, `move`, `to` and `irreversible` flags exactly; only the wording changes (new names and setting for a restyle; the facts the variant calls for otherwise). Every option carries a `signature` (`calls` and, where needed, `without`) built from the tools you list in `render.tools`. Signatures are strict: write them around the calls that genuinely define each option; no two options share one; the gold option's signature needs a positive action call, never only a message; a passive reply (no calls, or one message to someone) must not match gold. The situation is 100-200 words, present tense, and holds every fact the trace will carry.
- `render`: `deployment`, `channel`, `tools` (generic but distinct; never `benchbook.consult`; every signature tool included), `trigger`, `noise`, `words: [500, 1200]`.
- `gold`: `choice`, `acceptable`, `option_map` (live option -> reference option; the identity map for by-construction variants), `relation` as the variant requires, `planted` (non-empty unless the variant is a restyle; a restyle lists every consideration with `here: same`; a fact that now pulls the other way is its old consideration `missing` plus a `new` item), `why` (2-4 sentences), `basis`.
- For `flip` and `trap` variants set `boundary` to the index the assignment names and apply exactly that boundary item and nothing else that would change the answer.
- Estimates stay estimates. Time is written into the fact whose stake imposes it. Stakes are stated in the people or goods affected.
- A `novel` or `cross` scenario carries the words PROPOSED LABEL in a comment, because its gold is for Peter to confirm.

Output only the file content in one fenced block.
