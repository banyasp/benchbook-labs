"""Retrieval interface. Oracle = serve what the experiment designates for the arm; Structural = stub (later)."""
from __future__ import annotations

from bench.schema import Case, LiveScenario

from .store import Library


class OracleRetriever:
    """Serves the case(s) the scenario designates for the arm, in order. `none` serves nothing."""

    def __init__(self, lib: Library):
        self.lib = lib

    def retrieve(self, scenario: LiveScenario, arm: str) -> list[Case]:
        if arm not in scenario.arms:
            raise KeyError(f"scenario {scenario.id} has no arm `{arm}` (has {sorted(scenario.arms)})")
        return [self.lib.case(cid) for cid in scenario.arms[arm].served]


class StructuralRetriever:
    """PDF 'Casebook Search' / library-size scaling experiment: filter, then structural score over considerations
    (equity + polarity + weight, decisive counting double, plus tension, move structure, authority shape), then
    embeddings as tiebreak (DATA-PIPELINE-DESIGN-v1 section 4). Not built yet; see library.index for the tables."""

    def __init__(self, lib: Library, index_path=None, k: int = 1):
        self.lib, self.index_path, self.k = lib, index_path, k

    def retrieve(self, scenario: LiveScenario, arm: str | None = None) -> list[Case]:
        raise NotImplementedError("structural retrieval is a stub; use OracleRetriever")
