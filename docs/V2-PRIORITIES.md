# Benchbook — priorities for v2 (living list)

*Started 2026-10-26/27 during Peter's walkthrough of the data pipeline. Items Peter has explicitly marked for v2.
Order is priority. Keep every version (`docs/versions/`) before large edits.*

1. **Natural pairs (Peter: "definitely early on the v2 list").** Pair two *independently sourced* scenarios matched by
   structure (not derived by perturbation). v1 builds gold mappings only for derived pairs (perturb's Δ is the
   mapping) and decoys (nothing corresponds). Natural pairs have no Δ, so they need a **mapping step**: a model
   produces M^F and M^K between C and T, with a verification check, and the structural index to find candidate
   pairs. They carry the source-endorsed O(T), so they are also how the project measures closeness to the oracle
   (see `docs/HYPOTHESES.md`).
2. **Token space for derived facts (risk register R49, severe limitation).** v1 renders traces so every relevant
   fact is readable with at most a single-hop reading. v2 should let the reply derive implied facts before stating
   them (an inline `from` + `work` field, a separate inference step, or a less rigid structure).
3. **Multiple served cases** (C\* as a set; triangulating precedents).
4. **Near-neighbor arm** (Peter, 2026-10-27: defer to v2). The harness retrieves the nearest library case itself instead
   of serving the pair's own C, measuring the retrieval gap ‖AR_C\* − AR_C‖. Needs the structural index (built with #1).
5. **Fallback router and natsec sources** (design v2.4 §4.2): route false-positive refusals of in-scope decision content
   to another provider; then add use-of-force / intelligence-oversight decision sources tagged by `refusal_sensitivity`.
   (Router is T2 in v1; listed here so the natsec domain expansion isn't forgotten.)
