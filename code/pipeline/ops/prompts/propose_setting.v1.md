You propose the SETTING for a sister of an ANCHOR decision scenario, for a benchmark that tests reasoning by analogy.
The sister keeps the anchor's considerations exactly (the same equities, each favoring the same option with the same
weight) and the same verdict, but its facts describe a different situation.

MODE tells you how far to move:
- neighbor: the SAME national-security sub-domain as the anchor, a DIFFERENT situation (another organization, period,
  event or set of actors). Not the anchor reworded.
- transfer: a DIFFERENT national-security sub-domain (e.g. personnel security, export control, arms control,
  counterintelligence, alliance management, space policy, homeland security, sanctions, defense acquisition, cyber
  policy, diplomatic security, intelligence oversight), chosen so that every consideration carries over naturally.

Choose a setting whose own law, institutions or stakes do NOT add a strong consideration the anchor lacks (that would
change the weighing). Stay at the level of decision ethics, law, policy and judgment: no weapons employment,
targeting, intrusion, surveillance or collection technique.

Return one JSON object only:
{"subdomain": "<sub-domain>", "title": "<short title>",
 "sketch": "<4-7 sentences: who decides what, the options in the sister's terms, and how each anchor consideration shows up>",
 "option_map": {"O1": "<the sister's O1 in a few words>", ...},
 "risk": "<one sentence: what in this setting could add a consideration, or 'none'>"}
