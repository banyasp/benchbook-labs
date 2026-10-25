"""Proof that the live-check exports load: SFT in training.sft_data, RLVR in scorers (StubJudge)."""
from bench.schema import parse_reply
from scorers import StubJudge, score_reply
from scorers.trl_adapter import to_key, to_served, reward_funcs
from training.sft_data import load_jsonl, verify

D = "results/p3-livecheck/data/exports/v0/"
rl = load_jsonl(D + "rl/rlvr.jsonl")[0]
sft = load_jsonl(D + "sft/sft.jsonl")[0]
print("rl columns:", sorted(rl))
print("sft columns:", sorted(sft))
print("sft_data.verify:", verify(sft))
s = score_reply(parse_reply(sft["prefill"] + sft["completion"]), to_key(rl["answer_key"]), to_served(rl["served"]), StubJudge())
print({k: s[k] for k in ("schema_valid", "verdict_choice", "relation", "governs", "via_match", "facts_mapping",
                         "considerations_mapping", "facts_enum", "considerations_enum")})
f = reward_funcs(StubJudge(), ["verdict_choice", "relation"])
print("TRL reward funcs:", [fn([rl["prompt"]], [sft["completion"]], answer_key=[rl["answer_key"]], served=[rl["served"]]) for fn in f])
ev = load_jsonl(D + "eval/inspect.jsonl")[0]
print("eval keys:", sorted(ev), "metadata:", sorted(ev["metadata"]), "target:", ev["target"])
print("prefill:", repr(sft["prefill"]))
