"""GRPO skeleton (TRL GRPOTrainer): Dr. GRPO normalization, 8 rollouts, KL (beta) to the SFT checkpoint.

The reward function is TBD (Peter). `build_trainer(..., reward_fn=...)` takes a callable
    reward_fn(prompt: str, completion: str, example: dict) -> float | None
(`completion` is the generated text; prefill is in the prompt; `example` is the dataset row, which carries
scenario/arm/mode/prompt flag). There is no default: without `--placeholder-reward` (or a callable passed in
from Python) it raises. The placeholder uses only the scorers' choice score (0 when there is no verdict).

TRL names relied on (trl 1.12.0): GRPOConfig(loss_type="dr_grpo", scale_rewards="none", beta, num_generations,
max_completion_length, use_vllm, temperature, top_p, generation_batch_size); GRPOTrainer(model, reward_funcs,
args, train_dataset, processing_class, peft_config). With a PEFT model that already holds the SFT adapter and
beta != 0, TRL copies it into a frozen "ref" adapter, so the KL is to the SFT checkpoint (not the base model).

    # CPU smoke (tiny random Granite, use_vllm=False, 2 steps):
    PYTHONPATH=code CUDA_VISIBLE_DEVICES= HF_HUB_OFFLINE=1 python -m training.grpo --smoke
    # real run (later): python -m training.grpo --sft-adapter results/sft/run1/adapter --placeholder-reward --out results/grpo/run1
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Callable

from . import common

DEFAULT_CONFIG = common.HERE / "configs" / "grpo.v1.yaml"
RewardFn = Callable[[str, str, dict], "float | None"]


class RewardNotDefined(RuntimeError):
    pass


def missing_reward(*_a, **_k):
    raise RewardNotDefined("The reward function is TBD (Peter). Pass reward_fn=... to build_trainer, or use "
                           "--placeholder-reward (choice score only) for plumbing tests.")


def trl_reward(reward_fn: RewardFn | None, name: str = "reward"):
    """Adapt reward_fn(prompt, completion, example) to TRL's reward_funcs signature."""
    if reward_fn is None:
        missing_reward()

    def f(prompts, completions, completion_ids=None, **cols):
        out = []
        for i, (p, c) in enumerate(zip(prompts, completions)):
            ex = {k: v[i] for k, v in cols.items() if isinstance(v, (list, tuple)) and len(v) == len(prompts)}
            if isinstance(c, list):                        # conversational format: [{"role":..., "content":...}]
                c = c[-1]["content"]
            out.append(reward_fn(p, c, ex))
        return out
    f.__name__ = name
    return f


def placeholder_choice_reward(lib, judge, backend, settings_extra=None) -> RewardFn:
    """Choice score only (1 correct / 0 wrong or no verdict). Placeholder until Peter defines the reward; uses the
    same scorer function as evaluation. Episodes are rebuilt per (scenario, arm, mode, prompt) to get `served`."""
    from bench.schema import parse_reply
    from eval import score_names
    cache = {}

    def fn(prompt, completion, ex):
        sc = lib.scenario(ex["scenario"])
        k = (ex["scenario"], ex["arm"], ex["mode"], ex["analogical_prompt"])
        if k not in cache:
            st = backend.make_settings(mode=ex["mode"], analogical_prompt=ex["analogical_prompt"], **(settings_extra or {}))
            cache[k] = backend.build_episode(sc, ex["arm"], st, lib)
        ep = cache[k]
        parsed = parse_reply((getattr(ep, "prefill", "") or "") + completion, noref=ex["arm"] == "none")
        if (parsed.steps.get("verdict") or {}).get("choice") is None:
            return 0.0
        v = score_names.get(backend.score_reply(parsed, sc.answer_key(ex["arm"]), ep.served, judge), "choice")
        return 0.0 if v is None else float(v)
    return fn


def grpo_config(cfg: dict, out: str, smoke: bool = False):
    from trl import GRPOConfig
    from bench.models import role
    g = dict(cfg["grpo"])
    r = role(cfg.get("policy_role", "policy"))
    if g.get("max_completion_length") is None:
        g["max_completion_length"] = r.get("max_tokens", 12000)
    if g.get("temperature") is None:
        g["temperature"] = r.get("temperature", 1.0)
    if g.get("top_p") is None:
        g["top_p"] = r.get("top_p", 1.0)
    kw = dict(output_dir=out, report_to="none", **g)
    if smoke:
        kw.update(max_steps=2, num_train_epochs=1, bf16=False, use_cpu=True, gradient_checkpointing=False, use_vllm=False,
                  per_device_train_batch_size=8, gradient_accumulation_steps=1, max_completion_length=12,
                  save_strategy="no", learning_rate=1e-3, logging_steps=1, temperature=1.0, top_p=1.0)
    assert kw["loss_type"] == "dr_grpo" and kw["scale_rewards"] in ("none", False), "Dr. GRPO settings changed"
    return GRPOConfig(**kw)


def build_trainer(cfg: dict, model, tokenizer, dataset, reward_fn: RewardFn | None, out: str, smoke: bool = False,
                  peft_config=None):
    """`model`: a PeftModel holding the SFT adapter (trainable) -> KL to SFT; or a base model + `peft_config`
    (fresh LoRA, then KL is to the base model). Dataset rows need a `prompt` string (the rendered prompt)."""
    from trl import GRPOTrainer
    return GRPOTrainer(model=model, reward_funcs=trl_reward(reward_fn), args=grpo_config(cfg, out, smoke),
                       train_dataset=dataset, processing_class=tokenizer, peft_config=peft_config)


def smoke_reward(prompt, completion, ex):
    """Plumbing-only reward for the CPU smoke (a random tiny model emits noise: reward = a random-ish function of
    length so that group variance is non-zero). Never a real reward."""
    return float(len(completion) % 3)


def smoke(cfg: dict) -> dict:
    import torch
    from datasets import Dataset
    from peft import PeftModel, get_peft_model
    from training.sft_lora import lora_config
    common.force_cpu()
    tok = common.load_tokenizer(common.policy_hf_id(cfg))
    tok.padding_side = "left"
    out = tempfile.mkdtemp(prefix="grpo_smoke_")
    # 1. a stand-in "SFT checkpoint": a LoRA adapter on the tiny model, saved and reloaded trainable (the real path)
    base = common.tiny_model(len(tok), seed=1)
    base.config.pad_token_id = tok.pad_token_id
    peft = get_peft_model(base, lora_config(cfg["lora"]))
    for n, p in peft.named_parameters():                       # make the "SFT" adapter non-trivial (B starts at 0)
        if "lora_B" in n:
            torch.nn.init.normal_(p, std=0.02)
    peft.save_pretrained(Path(out) / "sft_adapter")
    base2 = common.tiny_model(len(tok), seed=1)
    base2.config.pad_token_id = tok.pad_token_id
    model = PeftModel.from_pretrained(base2, Path(out) / "sft_adapter", is_trainable=True)
    prompts = [r["prompt_text"] for r in common.smoke_golden(tok, 2)]
    ds = Dataset.from_list([{"prompt": p, "scenario": f"S{i}", "arm": "relevant", "mode": "B", "analogical_prompt": True}
                            for i, p in enumerate(prompts)])
    tr = build_trainer(cfg, model, tok, ds, smoke_reward, out, smoke=True)
    a = tr.args
    assert (a.loss_type, a.scale_rewards, a.num_generations, a.beta > 0) == ("dr_grpo", "none", 8, True)
    assert tr.ref_model is None and "ref" in tr.model.peft_config, "reference should be the copied SFT adapter"
    before = {k: v.clone() for k, v in tr.model.state_dict().items() if "lora_" in k and ".default." in k}
    ref_before = {k: v.clone() for k, v in tr.model.state_dict().items() if ".ref." in k}
    tr.train()
    after = tr.model.state_dict()
    moved = [k for k in before if not torch.equal(before[k], after[k])]
    ref_moved = [k for k in ref_before if not torch.equal(ref_before[k], after[k])]
    logs = [h for h in tr.state.log_history if "loss" in h or "reward" in h]
    res = {"steps": tr.state.global_step, "num_generations": a.num_generations, "loss_type": a.loss_type,
           "scale_rewards": a.scale_rewards, "beta": a.beta, "use_vllm": a.use_vllm,
           "policy_adapter_tensors_moved": len(moved), "ref_adapter_tensors_moved": len(ref_moved),
           "ref_adapter_tensors": len(ref_before), "log_keys": sorted({k for h in logs for k in h})[:12]}
    assert res["steps"] == 2 and res["policy_adapter_tensors_moved"] > 0 and res["ref_adapter_tensors_moved"] == 0, res
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--placeholder-reward", action="store_true", help="reward = scorers' choice score only (plumbing)")
    ap.add_argument("--sft-adapter", help="path of the SFT LoRA adapter (policy init and KL reference)")
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--judge", choices=["jev", "stub"], default="jev")
    ap.add_argument("--out", default="results/grpo/run")
    a = ap.parse_args(argv)
    cfg = common.load_config(a.config)
    if a.smoke:
        print(json.dumps(smoke(cfg), indent=1))
        return 0
    reward_fn = None
    if a.placeholder_reward:
        from eval import core
        from library import Library
        lib = Library(root=a.data_root)
        reward_fn = placeholder_choice_reward(lib, core.default_judge(a.judge), core.default_backend())
    else:
        missing_reward()       # fails fast, before any model is loaded
    import torch
    from datasets import Dataset
    from eval import core
    from peft import PeftModel
    from transformers import AutoModelForCausalLM
    name = common.policy_hf_id(cfg)
    tok = common.load_tokenizer(name)
    tok.padding_side = "left"
    be = core.default_backend()
    lib = Library(root=a.data_root)
    d = cfg["data"]
    rows = []
    for sc in lib.scenarios(split=d["split"]):
        for arm in sc.arms:
            if arm not in d["arms"]:
                continue
            for mode in d["modes"]:
                for p in d["prompts"]:
                    ep = be.build_episode(sc, arm, be.make_settings(mode=core.HARNESS_MODE[mode], analogical_prompt=p), lib)
                    rows.append({"prompt": ep.prompt_text, "scenario": sc.id, "arm": arm, "mode": core.HARNESS_MODE[mode],
                                 "analogical_prompt": p})
    ds = Dataset.from_list(rows)
    model = AutoModelForCausalLM.from_pretrained(name, dtype=torch.bfloat16)
    peft_config = None
    if a.sft_adapter:
        model = PeftModel.from_pretrained(model, a.sft_adapter, is_trainable=True)
    else:
        from peft import LoraConfig
        c = cfg["lora"]
        peft_config = LoraConfig(r=c["r"], lora_alpha=c["alpha"], lora_dropout=c["dropout"],
                                 target_modules=c["target_modules"], task_type="CAUSAL_LM")
    tr = build_trainer(cfg, model, tok, ds, reward_fn, a.out, peft_config=peft_config)
    tr.train()
    tr.save_model(str(Path(a.out) / "adapter"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
