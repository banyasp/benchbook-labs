from collections import Counter

from eval.allpairs import confirm_schedule, grid_schedule, sid_of


def test_grid_schedule_covers_every_cell_once_and_rounds_are_balanced():
    x = [f"X{i}" for i in range(5)]
    items = grid_schedule(x, x, k_control=3, run_seed=0)
    grid = [(it["x1"], it["x2"]) for it in items if it["phase"] == "grid"]
    assert sorted(grid) == sorted((a, b) for a in x for b in x)            # self cells included, no repeats
    ctrl = Counter(it["x1"] for it in items if it["phase"] == "control")
    assert all(ctrl[a] == 3 for a in x)
    assert len({sid_of(it, "base") for it in items}) == len(items)
    # first 2*len(x) items: control idx 0 and the self cells; then each round has one cell per X1
    head = items[:2 * len(x)]
    assert {it["phase"] for it in head[:len(x)]} == {"control"} and all(it["x1"] == it["x2"] for it in head[len(x):])
    first_round = [it for it in items[2 * len(x):] if it["phase"] == "grid"][:len(x)]
    assert sorted(it["x1"] for it in first_round) == x


def test_confirm_picks_only_successful_non_self_x2():
    S = [{"model": "base", "phase": "grid", "x1": "A", "x2": "A", "correct": 1.0},
         {"model": "base", "phase": "grid", "x1": "A", "x2": "B", "correct": 0.0},
         {"model": "base", "phase": "grid", "x1": "A", "x2": "C", "correct": 1.0},
         {"model": "base", "phase": "grid", "x1": "B", "x2": "A", "correct": 0.0},
         {"model": "base", "phase": "grid", "x1": "B", "x2": "B", "correct": 1.0}]
    items, picks = confirm_schedule(S, k=4, run_seed=0, model="base")
    assert picks == {"A": "C", "B": None}
    assert [(i["x1"], i["x2"], i["idx"]) for i in items] == [("A", "C", j) for j in range(1, 5)]
