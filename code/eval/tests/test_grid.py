"""Core grid runner + report, fakes only (no server, no judge, no GPU)."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from bench.schema import LiveScenario
from eval import grid, grid_report
from eval.core import LEGACY_ARMS, canon_record, read_samples

from .fakes import GOOD, broken, key_for

PREFILL = "<think>\nkind: fact_enumeration\n"


def row(pair, arm, fam, d=None, cell="core", ar=True, intent="restyle", domain="d1", held=False, tags=(), rel_d=None,
        partner=None, gold_move="act"):
    key = key_for(pair, arm if arm in ("none", "relevant", "decoy") else "relevant")
    k = key.model_dump(by_alias=True, exclude_none=True)
    k["arm"] = arm
    k["options"]["LIVE-O3"]["move"] = gold_move
    return {"id": f"{pair}:full:ar{int(ar)}:eq1", "input": [], "prompt_text": "PROMPT", "prefill": PREFILL, "target": "LIVE-O3",
            "metadata": {"answer_key": k, "served": "[]", "pair": pair, "arm": arm, "cell": cell, "card_view": "full", "AR": ar,
                         "equities_on": True, "intent": intent, "relation": "follows", "realization": None, "tier": "by-construction",
                         "family": fam, "domain": domain, "held_out": held, "split": "eval-only", "tags": list(tags), "d": d,
                         "trace_relevant_d": rel_d, "restyle_partner": partner, "scenario": f"T-{pair}", "case": "DR-PDF-001@v1",
                         "recommended_option": None, "settings": {}}}


class FakeServer:
    def __init__(self):
        self.calls, self.models = 0, []

    async def arun(self, ep, settings):
        self.calls += 1
        self.models.append(settings.model)
        assert settings.mode == "C" and ep.prefill == PREFILL
        text = GOOD if settings.model == "sft" else (broken(GOOD, "no_verdict") if settings.seed % 2 else GOOD)
        return SimpleNamespace(content=text, reasoning=None, raw_text=text, seconds=1.0, finish_reason="stop",
                               usage={"prompt_tokens": 100, "completion_tokens": 50})

    @staticmethod
    def score(parsed, key, served, judge):
        ch = (parsed.steps.get("verdict") or {}).get("choice")
        return {"choice": None if ch is None else float(key.correct(ch)),
                "translated_choice": ch if ch in key.options else None, "gold_option_present": 1}

    def backend(self):
        return grid.GridBackend(self.arun, self.score, lambda **kw: SimpleNamespace(**kw))


def rows(n=6):
    out = []
    for i in range(n):
        f = f"F{i % 3}"
        out.append(row(f"P-rel{i}", "relevant", f, d=0.1 * i, rel_d=0.1 * i))
        out.append(row(f"P-none{i}", "none", f, rel_d=0.1 * i))
        out.append(row(f"P-rev{i}", "revised", f, d=0.0, partner=f"P-rel{i}", intent="revised"))
    out.append(row("P-dec", "decoy", "F0", d=0.9))
    out.append(row("P-self", "self", "F1", d=0.0, intent="self"))
    out.append(row("P-ho", "relevant", "FH", d=0.5, domain="military-operational", held=True))
    out.append(row("P-imp", "relevant", "FI", d=0.5, tags=("eval-only-import",)))
    out.append(row("P-ar0", "relevant", "F0", d=0.2, cell="ar_off", ar=False))
    return out


def run(tmp_path, rs, **kw):
    srv = FakeServer()
    m = asyncio.run(grid.run_grid(rs, tmp_path / "run", backend=srv.backend(), judge=None, progress_every=0, **kw))
    return srv, m


def test_grid_runs_both_models_and_resumes(tmp_path):
    rs = grid.load_export(_write(tmp_path, rows()), cells=("core",))
    assert all(r["metadata"]["cell"] == "core" for r in rs) and len(rs) == 6 * 3 + 4
    srv, m = run(tmp_path, rs, models=("base", "sft"), concurrency=8)
    got = read_samples(tmp_path / "run" / "samples.jsonl")
    assert len(got) == 2 * len(rs) == srv.calls and m["errors"] == 0
    assert set(srv.models) == {"granite-4.2-8b", "sft"}                 # base and adapter model names
    assert {r["arm"] for r in got} >= {"none", "relevant", "revised", "decoy", "self"}
    sft = [r for r in got if r["model"] == "sft"]
    assert all(r["correct"] == 1.0 for r in sft) and any(r["correct"] == 0.0 for r in got if r["model"] == "base")
    assert (tmp_path / "run" / got[0]["raw_path"]).exists()
    srv2, m2 = run(tmp_path, rs, models=("base", "sft"))                # resumable: nothing re-run
    assert srv2.calls == 0 and m2["ran"] == 0 and len(read_samples(tmp_path / "run" / "samples.jsonl")) == len(got)
    srv3, _ = run(tmp_path, rs[:2], models=("base",), n=2)              # n=2 adds idx 1 only
    assert srv3.calls == 2


def _write(tmp_path, rs):
    p = tmp_path / "inspect.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rs))
    return p


def test_cells_are_opt_in(tmp_path):
    p = _write(tmp_path, rows())
    assert len(grid.load_export(p, cells=("core", "ar_off"))) == len(grid.load_export(p)) + 1
    assert len(grid.load_export(p, arms=["none"])) == 6


def test_error_is_logged_and_retried_on_resume(tmp_path):
    rs = grid.load_export(_write(tmp_path, rows(1)), arms=["relevant"])
    srv = FakeServer()
    orig = srv.arun
    state = {"n": 0}

    async def flaky(ep, settings):
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError("503")
        return await orig(ep, settings)
    srv.arun = flaky
    asyncio.run(grid.run_grid(rs, tmp_path / "r", backend=srv.backend(), judge=None, models=("base",), progress_every=0, concurrency=1))
    assert (tmp_path / "r" / "errors.jsonl").read_text().count("503") == 1
    assert len(read_samples(tmp_path / "r" / "samples.jsonl")) == len(rs) - 1
    asyncio.run(grid.run_grid(rs, tmp_path / "r", backend=srv.backend(), judge=None, models=("base",), progress_every=0))
    assert len(read_samples(tmp_path / "r" / "samples.jsonl")) == len(rs)


def test_report_sections_and_figures(tmp_path):
    rs = grid.load_export(_write(tmp_path, rows()), cells=("core", "ar_off"))
    run(tmp_path, rs, models=("base", "sft"))
    figs = tmp_path / "res" / "figures"
    md = grid_report.build([tmp_path / "run"], figs, "t", n_boot=50)
    for h in ("Headline", "By arm", "Off-menu", "Baselines", "enumerated", "follow both", "Decoy vs none", "% incorrect irreversible",
              "Within-family", "Breakdowns", "Held-out domain", "Pilot imports", "Second-pass"):
        assert h in md, h
    assert "100% by construction" in md
    for f in ("headline-t.png", "by-arm-t.png", "within-family-t.png"):
        assert (figs / f).stat().st_size > 1000
    # held-out and imports are not in the main sections
    main_part = md.split("## 11.")[0]
    held = md.split("## 11.")[1].split("## 12.")[0]
    assert "military" not in main_part and "base" in held or "No held-out" in held
    assert "ar_off" in md.split("## 13.")[1]


def test_baselines_and_copy_case():
    rs = [{"model": "base", "pair": f"p{i}", "arm": "relevant", "domain": "a", "gold_move": m, "copy_available": True,
           "copy_correct": c} for i, (m, c) in enumerate([("act", True), ("act", True), ("ask", False)])]
    b = grid_report.baselines(rs)["relevant"]
    assert b["always_act"] == pytest.approx(2 / 3) and b["always_hand_up"] == pytest.approx(1 / 3) and b["copy_case"] == pytest.approx(2 / 3)
    assert b["majority_domain"] == pytest.approx(2 / 3)       # leave-one-out: act (tie -> alphabetical) and act hit, ask predicted act misses


def test_copy_case_translates_through_option_map():
    key = key_for("S", "relevant")
    served = [SimpleNamespace(doc={"case": {"verdict": {"choice": "REF1-O1"}}}, table={"REF1-O1": "DR-PDF-001@v1/O1"})]
    out = grid.copy_case(key, served)
    assert out["copy_available"] and out["copy_correct"] is True      # fixture: case O1 maps to live O3 = gold
    assert grid.copy_case(key_for("S", "none"), []) == {"copy_available": False, "copy_correct": None}


def test_legacy_augmented_arm_loads_as_revised(tmp_path):
    assert LEGACY_ARMS == {"augmented": "revised"}
    r = canon_record({"arm": "augmented", "item_id": "S|augmented|prompt|C"})
    assert r["arm"] == "revised" and r["item_id"] == "S|revised|prompt|C"
    sc = LiveScenario.model_validate({
        "id": "X-v01", "family": "X", "trace": "t.json", "equities": "pilot",
        "arms": {"none": {"served": [], "key": "k"}, "augmented": {"served": ["DR-X@v1"], "key": "k"}},
        "perturbation": {"variant": "restyle", "source_case": "DR-X@v1"}})
    assert list(sc.arms) == ["none", "revised"]
    with pytest.raises(ValueError):
        LiveScenario.model_validate({"id": "X", "family": "X", "trace": "t", "equities": "p", "perturbation": {"variant": "r", "source_case": "DR-X@v1"},
                                     "arms": {"augmented": {"served": ["DR-X@v1"], "key": "k"}, "revised": {"served": ["DR-X@v1"], "key": "k"}}})
