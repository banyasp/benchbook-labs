You check where a decision scenario's flip conditions come from. The scenario was extracted from a source document by
another model. Each flip condition says how the decision would or would not change if something were true:
`would_change` items {id, if, then} and `would_not_change` items {id, if}.

For each item, read the SOURCE EXCERPT and label it:
- stated: the source itself says (in its own words) that this condition would change, or would not change, the decision
  (e.g. an official says approval depended on it, or that it made no difference).
- implied: the source does not say so, but a careful reader would infer it directly from what the source says about the
  reasons for the decision.
- authored: neither; the extracting model supplied it.

Return one JSON object only:
{"items": [{"id": "<item id>", "label": "stated|implied|authored", "quote": "<the shortest source passage that supports
stated or implied, else empty>", "why": "<one sentence>"}]}
Label every item given. Be strict: "stated" needs the source to make the counterfactual link itself.
