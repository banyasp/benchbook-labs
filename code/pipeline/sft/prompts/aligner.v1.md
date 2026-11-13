You align two decision scenarios item by item, for a training answer key. LIVE is the situation an agent
faces; CASE is a reference case served to it. You classify ids; you write no prose except a one-line reason per pair.

Definitions.
- facts: matched = the same fact in both (same characteristic, same state, wording may differ); corresponding = the same
  characteristic of the situation in a different state, or the same role in the argument played by a different
  concrete fact in a different setting (for example "the analyst reviews at 0600" and "the officer reviews at 0730");
  every other fact is only in its own scenario. Each id appears in at most one pair.
- considerations: matched = same equity, same direction and weight, doing the same work; corresponding = same equity,
  different manner or size; otherwise only in its own scenario. One-to-one.
- frame: compare the decision question, who decides, and the agent's role: same | same_kind | different.
- governs: true if the case's considerations are close enough that its reasoning should govern the live decision
  (decided on considerations, not on shared surface facts); false otherwise.
{known}
LIVE ({x1}):
{live}

CASE ({x2}):
{case}

Answer with one YAML document and nothing else:
frame: {{question: same | same_kind | different, decider: same | same_kind | different, role: same | same_kind | different}}
facts:
  matched: [[F1, F1], ...]          # [live id, case id], bare ids as printed above
  corresponding: [[F2, F3], ...]
{cons_block}governs: true | false
governs_why: "one sentence"
