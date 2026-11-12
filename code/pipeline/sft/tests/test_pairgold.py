"""pairgold on the pairs-v1 pilot cells (lineage arms only: no LLM). Skipped where the box's data is absent."""
import json
from pathlib import Path

import pytest

from bench.models import ROOT

CELLS = ROOT / "data/datasets/pairs-v1/cells-pilot.json"
pytestmark = pytest.mark.skipif(not CELLS.exists(), reason="pairs-v1 pilot cells not on this machine")


def _cells(arm, n=10):
    return [c for c in json.load(open(CELLS)) if c["arm"] == arm][:n]


def _no_llm(_):
    raise AssertionError("lineage arms must not call the aligner")


@pytest.mark.parametrize("arm", ["self", "same_domain_flip", "noflip", "revised"])
def test_lineage_arms_build_without_llm(arm):
    from pipeline.project.project import gold_for
    from pipeline.sft.pairgold import pair_gold
    from pipeline.store import Store
    store = Store()
    for c in _cells(arm):
        b = pair_gold(store, c, call=_no_llm)
        g, _ = gold_for(b.pair, store, C=b.C, T=b.T)
        assert b.pair.governs
        if arm == "same_domain_flip":
            assert b.pair.relation == "flips" and g.via, c["cell"]
            # the back-flip item's `then` is X1's gold under the option map
            w = next(x for x in b.C.case.flip_conditions.would_change if b.C.case.global_id(x.id) == b.pair.via[0])
            assert b.pair.options_map[b.pair.choice] == b.C.case.global_id(w.then)
        else:
            assert b.pair.relation == "follows"
        if arm == "revised":
            assert b.pair.choice.endswith("/" + c["key"])
        if arm == "self":
            assert not b.pair.fact_map.live_only and not b.pair.fact_map.case_only


def test_emit_roundtrip():
    import yaml
    from pipeline.sft.targets import emit
    docs = [{"kind": "verdict", "choice": "LIVE-O1", "course": "Do it: now.", "relation": "flips", "via": ["REF1-flip2"],
             "decisive": ["LIVE-C1"], "now": ["a: b"], "flip_conditions": {"would_change": [
                 {"id": "LIVE-flip1", "if": "x, y", "then": "LIVE-O2", "why": "z"}], "would_not_change": [],
                 "watch_for": []}}]
    assert list(yaml.safe_load_all(emit(docs))) == docs
