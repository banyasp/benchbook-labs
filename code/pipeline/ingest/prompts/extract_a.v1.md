# extract_a.v1 -- the answer (considerations, reasoning, verdict, flip conditions) from the source's own reasons

You write the ANSWER half of a decision scenario whose facts and question frame are already fixed. The answer is the
source's, not yours: the verdict is the source's ENDORSED outcome, and the reasoning is the source's own stated
reasons, restated. Scope: decision ethics, law and policy only.

## The document
Each line is `[span id] text`.

{{SPANS}}

## The decision
{{FOCUS}}

## Facts and question frame (fixed; do not change)
{{FQ}}

The source's real outcome is option {{REAL}}. Your verdict `choice` MUST be {{REAL}}.

## Equities (use these ids only; pick the closest if none fits exactly and say so in `equity_gaps`)
{{EQUITIES}}

## What to produce
One JSON object, nothing else (no prose, no code fence):

- `considerations`: 3-6 items `{"id": "C1", "facts": ["F2", ...], "equity": "<equity id>", "favors": ["O1", ...], "weight": "strong|weak|bar", "why": "..."}`
  (`bar` only if the consideration rules options out outright, then add `"rules_out": ["O2"]`). Facts cited must
  exist above. Each consideration is one reason the source itself weighs or applies (the rule, the mitigating
  or aggravating condition, the evidence).
- `reasoning`: object with string fields `read` (what the situation really is, and the trap in it), `weighing`
  (how the considerations balance, citing the source's stated reasons, and what the balance depends on),
  `tradecraft` (decision practice only: how to carry the decision out and record it), `uncertainty`,
  `handoff` (decide alone, or involve whom, and why), `tempting_wrong` `{"option": "O?", "pull": "...", "why_wrong": "..."}`,
  and `rejected` mapping each non-chosen option id to one sentence on why it was not chosen. Inside prose you may
  refer to items as `{O2}`, `{F3}`, `{C1}`, `{flip1}` (curly braces ONLY for real ids).
- `verdict`: `{"choice": "{{REAL}}", "basis": "recommended|settled|contested", "decisive": ["C1", ...]}`.
  `settled` = a binding rule or authority states the outcome; `recommended` = the authority's judgment on the
  balance; `contested` = the source records real disagreement.
- `basis_statement`: who endorsed the outcome, in the source's words (a short quotation or close paraphrase naming
  the office, e.g. the Administrative Judge's conclusion; or the regulation's example and the issuing office).
- `flip_conditions`: `{"would_change": [{"id": "flip1", "if": "...", "then": "O?", "why": "...", "origin": "stated|authored", "spans": [...]}], "would_not_change": [{"id": "noflip1", "if": "...", "why": "...", "origin": "stated|authored", "spans": [...]}], "watch_for": [{"id": "watch1", "what": "...", "favors": ["O?"], "why": "...", "origin": "stated|authored", "spans": [...]}]}`.
  Mark `origin: stated` ONLY where the source itself states the counterfactual (e.g. "had the Individual ...",
  "if the Individual were to ...", or a mitigating condition it says was not met) and cite the spans; otherwise
  `authored` with `spans: []`. Give 1-3 would_change, 1-2 would_not_change, 0-2 watch_for. `then` is an option id.
- `lesson`: 2-3 sentences, the transferable rule.
- `limits`: 1-3 sentences, where this scenario's reasoning stops applying.
- `authored`: the field paths (like `reasoning.tradecraft`, `reasoning.tempting_wrong`, `lesson`, `limits`,
  `reasoning.handoff`) that are your own synthesis rather than the source's stated reasons.
- `equity_gaps`: list of notes where an equity was only the closest fit ([] if none).
