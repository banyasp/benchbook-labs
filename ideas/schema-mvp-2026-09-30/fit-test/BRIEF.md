# Fit test brief: convert Hard Calls into the Benchbook MVP schema

## Why
Peter Banyas is simplifying the Benchbook schema to a minimum viable product. Every case must fit one
simple form (one decider, one decision at one moment, 2-4 options, 3-6 considerations, values from a
shared list of 28) and carry its judgment in short prose. We want to know how well real draft cases fit,
what is lost, and what the schema is missing. Your honest misfit log matters more than polished YAML.

## Read first (all in /home/claude/benchbook-schema/mvp/)
- `templates/reference.template.yaml`, `templates/live.template.yaml`, `templates/mapping.template.yaml`
- The worked example: `examples/AUT-001.reference.yaml`, `examples/AUT-101.live.yaml`, `examples/AUT-101.mapping.yaml`
- The validator/scorer: `code/mvp.py` (run `python3 code/mvp.py validate <files>`; `python3 code/mvp.py card <ref>`;
  `python3 code/mvp.py score <mapping> <live> <served ref>`)
- Source cases: `/home/claude/benchbook-schema/src/scenarios/hard-calls-v1/hard-calls-cases.yaml` (100 cases; read only yours)

## For each of your cases
1. **Reference** `<ID>.reference.yaml`. Convert the Hard Calls case:
   - Keep the situation text (trim to 100-200 words if needed; keep every fact a consideration uses).
   - Options: keep meaning, reword to similar length (in Hard Calls the gold option is the longest in 96 of 100),
     tag each with `move` (act | partial | ask | refuse).
   - Considerations: at most 6 (drop or merge the weakest; say which in the log). `value` from the 28 values in
     `code/mvp.py` (VALUES). Letter = option favored. strong | weak. One-sentence `why`.
   - `choice` = the Hard Calls outcome; `decisive` = its reason; `basis` = holding_basis.
   - Judgment prose, within these budgets: read <= 40 words, weighing <= 70, tradecraft <= 50,
     uncertainty <= 35, tempting_wrong pull + why_wrong <= 35, lesson <= 35, limits <= 45.
     Draw on holding, resolve_vs_escalate, agent_move, tempting_wrong_answer, flip whys, notes.
     `weighing` must say which value gave way to which and WHY HERE, with the conditions that make it hold.
     It must not be a list of the factors. `tradecraft` is decision practice (what to check first, order,
     reversible before irreversible, who is told, what is recorded), never operational technique.
   - Boundaries: `would_change` from flip_rules (1-3; `then` = option letter or `ask` for "escalate");
     `would_not_change` from downplay_trap (1-2); `watch_for` from watch_for (0-2).
   - `retrieval`: headnote, tension (2-3 values), cues.
   - Full card must stay under 700 words (`python3 code/mvp.py card`).
2. **Two live variants**, each `<ID>-vNN.live.yaml` with `reference: <ID>`:
   - one `flip` variant built from one of your would_change items (rewrite the situation so that change holds;
     gold choice = that item's `then`; if `then` is ask, the live options must include exactly one ask/partial option);
   - one `novel` variant: add ONE new consideration that the card does not list (not in would_change, would_not_change
     or watch_for), bearing on one of the case's values. Label gold yourself and mark `basis: recommended` and add
     a YAML comment `# PROPOSED LABEL - for Peter`.
   - `planted` lists the differences you built in (ref id + here, or ref: new + favors + value).
3. **Gold mappings**, `<ID>-vNN.mapping.yaml`, one per variant, served your reference. Under 450 words. They must
   validate and score full marks on outcome, relation and differences.
4. Run `python3 code/mvp.py validate` on all your files until no ERRORs (warnings are fine if explained in the log).

## Misfit log `LOG.md` (the most important output)
Per case, short bullets:
- What did not fit the simple form, and what you did (dropped/merged considerations, split decisions,
  options you had to rewrite, authority or timing structure that had to become prose).
- What the judgment prose captured that the Hard Calls fields did not, and what it still misses.
- Where the relation vocabulary (follows | flips | distinguished | not_governed) or the compare
  vocabulary (same | stronger | weaker | missing) was awkward or ambiguous.
- Any place the validator was wrong or too strict/lenient.
Then 3-5 bullets of overall schema suggestions, ranked, each with the smallest change that would fix it.

## Rules
- Write files only under your output folder (given in your task). Do not edit templates, examples or code.
- Stay at the level of decision ethics, law and policy. No weapons employment, targeting, intrusion,
  collection or covert-communication technique.
- Keep every [UNVERIFIED] mark the Hard Calls text carries. Do not add new factual claims about real events.
- Do not use WebFetch/WebSearch; everything you need is local.
- Final message: a 10-line summary (cases done, validator status, the top 3 misfits, the top 3 suggestions).
