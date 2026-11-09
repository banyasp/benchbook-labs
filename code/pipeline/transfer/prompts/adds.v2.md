You review a worked decision case for completeness. It lists the considerations its author weighed. Most well-written
cases miss nothing important; report a gap only when you are confident it matters.

Report a consideration ONLY if both hold:
1. This particular setting brings it in: its own law, institutions, people or stakes. Generic caveats that apply to
   any decision ("more information would help", "reputations matter", "privacy is always relevant") do not count.
2. A careful decision-maker in this setting would treat it as decisive or as a legal or policy bar: it could change
   the choice, not merely add nuance.

Use equity ids from the EQUITIES list. Return one JSON object only:
{"missing": [{"equity": "<id>", "favors": ["O1"], "weight": "strong|bar", "why": "<one sentence>"}]}
Use an empty list when nothing decisive is missing (the usual case).
