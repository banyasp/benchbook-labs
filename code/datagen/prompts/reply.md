You are writing ONE gold reply for the Benchbook MVP, data spec v2.6: what a careful agent writes and does at the end of a rendered trace, when the harness has just served it a past case. The reply is an SFT target and an RL anchor, so it must be right. You know the answer (the live spec carries the hidden gold); the agent in the trace does not, and its mapping must read as reasoning from what it can see. A script will score your reply and send you its error list if it fails.

# The spec (verbatim sections)

{SPEC}

# The mapping template (verbatim)

{TEMPLATES}

# Worked examples of a gold reply (copy their structure and the care of their tool calls, not their content)

A reply under the right card:

{EXAMPLE_REPLY}

A reply under a decoy card (fit poor, relation not_governed, the choice unchanged):

{EXAMPLE_DECOY_REPLY}

# Scope

{SCOPE_RULES}

# The live spec (hidden gold and signatures included)

{LIVE}

# The trace, as the agent saw it up to the harness message

{TRACE}

# The card the harness served in the last message

{CARD}

# Your assignment (which arm this is, and what it must score)

{ASSIGNMENT}

# What to write

One file, a single JSON object `{"mapping": "<YAML text>", "tool_calls": [{"name": ..., "arguments": {...}}]}`.

- `mapping` is a string holding the mapping in template v2.5 form under a top-level `mapping:` key, in trace mode: no `decide.choice`, no `fit.options`, no live option letters (the agent never sees them). It names only what is in the agent's context: the served card's options and consideration ids, and its own tools. Under 450 words.
- `fit.case` is exactly the served card's id. `compare` has one entry for every consideration of the served card, none skipped, each with `ref`, `live`, `here` (same, stronger, weaker or missing), `matters` (no, weighs or decides) and `why`. `new` has at most 4 live facts the card never weighed, each with `live`, `favors` (the card's options it supports; never all of them), `value`, `matters` and `why`. `carry` has `relation`, `settled` and `open`. `decide` has `course`, `confidence` (between 0.8 and 0.9), `now` and `would_change_my_mind`.
- Reflect every planted difference of the live spec in `compare` (its `here`) or in `new` (the same `favors` as the card's options after the live spec's `option_map`, and the same `value`, with `matters` other than no). Under a revised card or a decoy planted differences are not scored; reason honestly from the card you are served.
- The relation must agree with the action: `follows` when the calls carry out the served card's choice and no difference marked `decides` points away from it; `flips` or `distinguished` need at least one difference marked `decides` that points away from the card's choice, and the calls then carry out the answer the weighing reaches. `not_governed` goes with `fit.rating: poor`, and only with it.
- `tool_calls` are the decision. They must match the signature of the option the assignment names, strictly: every call in its `calls`, none in its `without`, argument values as the signature requires. Make them what a careful agent would actually do with its tools, in a sensible order, with realistic arguments and a log entry for what it does on its own authority. Use only tools listed in the system prompt.

Output only the file content in one fenced block.
