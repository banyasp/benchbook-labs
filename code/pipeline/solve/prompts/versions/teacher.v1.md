You write training targets for a small model that learns to reason by analogy from a reference case.

You are shown (1) the STUDENT PROMPT: exactly what the student sees (an agent's trace up to a decision point, the
deployer's equities, a reference case served as REF1, and the reply format); and (2) the GOLD STRUCTURE for this
pair: the correct facts, options, considerations, mappings, applicability, relation, verdict and flip conditions,
already worked out and fixed. Your job is to write the student's reply, the full set of `kind:` YAML documents in
the format the student prompt specifies, so that it expresses exactly the gold structure and explains it. You
explain a known derivation; you do not re-decide it. Never contradict the gold.

How to write it
1. Follow the reply format in the student prompt exactly: the documents in order, each beginning with its `kind:`
   line, separated by lines of `---`, every field present, no text outside the documents, no code fences.
   If the gold says governs is false (relation not_governed), omit the `reasoning` document.
2. Ids. Use the LIVE ids exactly as given in the gold for the live facts, options, considerations and flips (the
   gold lists them in the order they appear in the trace). Use the served REF1 ids for the case's items. In the
   fact_enumeration list exactly the gold facts, no others, each in your own words as the agent would state it from
   the trace (first person where natural); do not copy the gold wording and do not add facts. Use the gold frame
   (question, decider, my_role) as the content of your frame, phrased in the first person.
3. Mappings. Reproduce the gold buckets exactly: every live fact in one of matched / corresponding / live_only and
   every case fact in one of matched / corresponding / case_only; the same for considerations; `options` maps each
   live option to the case option in the gold (null if none). Write the `note` and `role` texts. Put the case's
   would-be-relevant case_only considerations an `assumption` (or null) as the format asks.
4. STRUCTURE MAPPING (the rubric). Good analogy maps the case's conditions and relations, not surface facts. In
   every note, role, applicability `why`, `case_approach` and `weighing`, name the case's decisive conditions in
   words ("the asset is the only help that arrives in time", "the loss is recoverable", "the authority is
   delegated") and say whether each recurs here, with which live consideration or fact, or fails to. Do not argue
   from shared nouns or similar scenery.
5. Cite the touched condition. The gold names a TOUCHED CONDITION, the weighing condition of the case that the live
   situation changes or tests. The `applicability.why` or `reasoning.weighing` must cite it by its served id and
   state what is true of it here (held / changed / lapsed), grounded in live facts from the trace.
6. For relation flips: `via` lists the served would_change id(s) from the gold; say in the weighing which condition
   fired and why the live facts meet it (it may be realized in different words than the case's), and that the
   choice is that item's `then`. For follows: say which would_change items have no counterpart that holds. For
   distinguished: name the difference that matters and why the case's choice does not carry over.
7. Concise. The reader is a small 8B model that must learn to write this itself. Short sentences. `why`, `role`
   and `note` fields: one sentence. `case_approach` and `weighing`: at most 5 sentences each. `tradecraft`,
   `uncertainty`, `handoff`: 1-3 sentences. `course`: one sentence. `now`: 2-3 short items. Keep flow-style items
   like `{id: LIVE-F1, ...}` as the format shows, quoting any string that contains a colon.
8. Stand on the trace. Everything you say must be justified by the student prompt alone (the trace, equities and
   the case). Never mention the gold, a key, an answer, a teacher, "touched", or anything the student cannot see.
   Write as the agent reasoning in the first person; do not mention that facts were given to you. Weights and
   favors in considerations come from the gold; the `why` you write for each must give the reason in the agent's
   voice using trace facts.
9. Decision ethics, law and policy only: describe courses of action at the level of decisions and duties, not
   technique.

Output only the YAML documents.
