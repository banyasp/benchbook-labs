from collections import Counter

from bench.schema.pipeline import Scenario
from pipeline.ingest.balance_options import _rename, check, permutation, relabel, targets


def test_permutation_moves_winner_and_keeps_others_in_order():
    assert permutation(3, 1, 3) == {"O1": "O3", "O2": "O1", "O3": "O2"}
    assert permutation(3, 2, 2) == {"O1": "O1", "O2": "O2", "O3": "O3"}
    assert permutation(4, 4, 1) == {"O4": "O1", "O1": "O2", "O2": "O3", "O3": "O4"}


def test_swap_never_chains_and_reaches_keys_lists_paths_prose():
    mp = {"O1": "O2", "O2": "O1"}
    d = {"options": {"O1": "a", "O2": "b"}, "favors": ["O1"], "choice": "O2", "path": "case.options.O1",
         "gid": "DR-x@v1/O2", "why": "The balance favors O1 over O2; O10 is not an option id here."}
    out = _rename(d, mp)
    assert out["options"] == {"O2": "a", "O1": "b"} and out["favors"] == ["O2"] and out["choice"] == "O1"
    assert out["path"] == "case.options.O2" and out["gid"] == "DR-x@v1/O1"
    assert out["why"] == "The balance favors O2 over O1; O10 is not an option id here."


def test_real_scenario_relabel_is_consistent():
    import glob
    f = next(p for p in sorted(glob.glob("data/store/scenarios/CORPUS-*/DR-*.yaml"))
             if len(Scenario.load(p).case.options) == 3)
    s = Scenario.load(f)
    win = int(s.case.verdict.choice[1:])
    for t in (1, 2, 3):
        mp = permutation(3, win, t)
        new = Scenario.model_validate(relabel(s.dump(), mp))
        check(s, new, mp)
        assert new.case.verdict.choice == f"O{t}" and list(new.case.options) == ["O1", "O2", "O3"]


def test_targets_are_balanced_per_group():
    class S:
        def __init__(self, i, n, split):
            self.id, self.split = f"s{i}", split
            self.case = type("C", (), {"options": {f"O{k}": 0 for k in range(1, n + 1)}})()
    ss = [S(i, 3, "train") for i in range(30)] + [S(100 + i, 2, "test") for i in range(9)]
    tg = targets(ss)
    c3 = Counter(tg[s.id] for s in ss[:30])
    c2 = Counter(tg[s.id] for s in ss[30:])
    assert set(c3.values()) == {10} and max(c2.values()) - min(c2.values()) <= 1
