"""Offline fakes for 2b (library), 2c (harness) and 2d (score_reply), built on the real bench schemas."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from bench.schema import AnswerKey, Perturbation, Touched, parse_reply

FIX = Path(__file__).resolve().parents[2] / "bench" / "fixtures" / "pdf_example"
GOOD = (FIX / "journalist.reply.yaml").read_text()


def key_for(scenario: str, arm: str, *, choice="LIVE-O3", move_of_gold="act", option_map=True) -> AnswerKey:
    base = AnswerKey.load(FIX / "journalist.answer_key.yaml").model_dump(by_alias=True)
    base.update(scenario=scenario, arm=arm, choice=choice)
    base["options"]["LIVE-O3"]["move"] = move_of_gold
    if arm == "none":
        base.update(served=None, relation=None, via=None, option_map=None)
    elif arm == "decoy":
        base.update(relation="distinguished", option_map=None)
    elif not option_map:
        base["option_map"] = None
    return AnswerKey.model_validate(base)


class FakeScenario:
    def __init__(self, sid, family, arms, variant="restyle"):
        self.id, self.family = sid, family
        self.arms = {a: SimpleNamespace(served=[] if a == "none" else ["DR-PDF-001@v1"]) for a in arms}
        self.perturbation = Perturbation(
            variant=variant, operator="revise fact", source_case="DR-PDF-001@v1",
            touched=[Touched(item="DR-PDF-001@v1/F1", item_kind="fact", change="revised"),
                     Touched(item="DR-PDF-001@v1/F2", item_kind="fact", change="added"),
                     Touched(item="DR-PDF-001@v1/C1", item_kind="consideration", change="influence")])

    def answer_key(self, arm):
        return key_for(self.id, arm)


class FakeCase:
    verdict = SimpleNamespace(choice="O1")

    def global_id(self, local):
        return f"DR-PDF-001@v1/{local}"


class FakeLib:
    def __init__(self):
        self._s = [FakeScenario("S1-v01", "FAM1", ["none", "relevant", "augmented", "decoy"]),
                   FakeScenario("S2-v01", "FAM2", ["none", "relevant"], variant="flip")]

    def scenarios(self, family=None, split=None):
        return [s for s in self._s if family is None or s.family == family]

    def case(self, cid):
        return FakeCase()


def broken(text: str, how: str) -> str:
    if how == "no_verdict":
        return text[: text.index("kind: verdict") - 4]
    if how == "prose":
        return "I think we should warn her.\n" + text.split("kind: fact_mapping")[0]
    return text


class FakeBackend:
    """Replies depend on the seed: 1 in 4 lack the verdict; the rest are the PDF's worked reply."""

    def __init__(self):
        self.calls = 0
        self.cont_calls: list[str] = []
        from eval.core import Backend
        self.backend = Backend(build_episode=self.build_episode, run_episode=self.run_episode,
                               continue_episode=self.continue_episode, score_reply=self.score_reply,
                               make_settings=self.make_settings)

    @staticmethod
    def make_settings(**kw):
        return SimpleNamespace(**kw)

    @staticmethod
    def build_episode(sc, arm, settings, lib):
        served = [] if arm == "none" else [SimpleNamespace(case_id="DR-PDF-001@v1", prefix="REF1")]
        return SimpleNamespace(served=served, arm=arm, messages=[], prompt_text="PROMPT", prefill="",
                               meta={"arm": arm, "revised": arm == "augmented"})

    def run_episode(self, ep, settings, role="policy"):
        self.calls += 1
        text = broken(GOOD, "no_verdict") if settings.seed % 4 == 0 else GOOD
        if settings.mode == "A":
            text = "<think>\nweighing things freely\n</think>\n" + text
        return SimpleNamespace(content=text, reasoning=None, raw_text=text, seconds=1.5, finish_reason="stop",
                               usage={"prompt_tokens": 1000, "completion_tokens": 700, "reasoning_tokens": 100})

    def continue_episode(self, ep, settings, partial):
        self.cont_calls.append(partial)
        p = parse_reply(partial)
        flipped = ep.meta.get("revised")
        enum = p.steps.get("consideration_enumeration", {}).get("considerations", [])
        if any(c.get("id") == "LIVE-C1" and c.get("weight") == "weak" for c in enum):
            flipped = True
        mp = p.steps.get("consideration_mapping")
        if mp is not None and not any(x.get("live") == "LIVE-C1" for x in mp.get("matched", [])):
            flipped = True
        verdict = GOOD[GOOD.index("kind: verdict"):]
        if flipped:
            verdict = verdict.replace("choice: LIVE-O3", "choice: LIVE-O1")
        # a real vLLM continuation returns only the new text; raw_text of the fake is the whole assistant text
        text = partial.rstrip("\n") + "\n---\n" + verdict
        return SimpleNamespace(content=text, reasoning=None, raw_text=text, seconds=0.5, finish_reason="stop",
                               usage={"prompt_tokens": 1000, "completion_tokens": 100})

    @staticmethod
    def score_reply(parsed, key, served, judge):
        v = parsed.steps.get("verdict") or {}
        ch = v.get("choice")
        return {"choice": None if ch is None else float(key.correct(ch)),
                "relation": None if ch is None else float(v.get("relation") == key.relation),
                "via": None, "options_enumeration": 1.0 if "fact_enumeration" in parsed.steps else 0.0,
                "options_omitted": 0, "schema_validator": float(parsed.strict_ok)}
