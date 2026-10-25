"""LoRA SFT with PEFT + TRL SFTTrainer on pre-masked examples from training.sft_data.

    # real run (GPU, later):
    PYTHONPATH=code python -m training.sft_lora --data golden.jsonl --out results/sft/run1
    # CPU smoke (2 optimizer steps on a tiny random Granite; no download, no GPU):
    PYTHONPATH=code CUDA_VISIBLE_DEVICES= HF_HUB_OFFLINE=1 python -m training.sft_lora --smoke

The dataset rows are {input_ids, attention_mask, labels} with labels = -100 on everything the model did not
generate. SFTTrainer is told `dataset_kwargs={"skip_prepare_dataset": True}` so TRL keeps our labels as they are
(its default collator pads labels with -100 and uses `labels` when present).
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from . import common, sft_data

DEFAULT_CONFIG = common.HERE / "configs" / "sft_lora.v1.yaml"


def lora_config(c: dict):
    from peft import LoraConfig
    return LoraConfig(r=c["r"], lora_alpha=c["alpha"], lora_dropout=c["dropout"], target_modules=c["target_modules"],
                      task_type="CAUSAL_LM")


def sft_args(cfg: dict, out: str, smoke: bool = False):
    from trl import SFTConfig
    t = dict(cfg["train"])
    kw = dict(output_dir=out, report_to="none", dataset_kwargs={"skip_prepare_dataset": True},
              remove_unused_columns=False, **t)
    if smoke:
        kw.update(max_steps=2, warmup_steps=0, num_train_epochs=1, bf16=False, use_cpu=True, gradient_checkpointing=False,
                  per_device_train_batch_size=2, gradient_accumulation_steps=1, logging_steps=1, save_strategy="no",
                  learning_rate=1e-2)
    return SFTConfig(**kw)


def train(cfg: dict, examples, model, tokenizer, out: str, smoke: bool = False):
    from trl import SFTTrainer
    ds = sft_data.to_hf_dataset(examples)
    trainer = SFTTrainer(model=model, args=sft_args(cfg, out, smoke), train_dataset=ds, processing_class=tokenizer,
                         peft_config=lora_config(cfg["lora"]))
    trainer.train()
    return trainer


def smoke(cfg: dict) -> dict:
    """2 steps on CPU. Checks: loss finite, only LoRA weights moved, labels are masked outside the reply."""
    import torch
    common.force_cpu()
    name = common.policy_hf_id(cfg)
    tok = common.load_tokenizer(name)             # tokenizer only (a few MB); the model is random and tiny
    recs = common.smoke_golden(tok, 4)
    ex, rej = sft_data.build_examples(recs, tok, True, 4096)
    assert ex and not rej, rej
    for e, r in zip(ex, recs):
        assert not sft_data.check_example(tok, e, r["prompt_text"], r["completion"])
    model = common.tiny_model(len(tok))
    before = {k: v.clone() for k, v in model.state_dict().items()}
    out = tempfile.mkdtemp(prefix="sft_smoke_")
    tr = train(cfg, ex, model, tok, out, smoke=True)
    logs = [h for h in tr.state.log_history if "loss" in h]
    after = tr.model.state_dict()
    moved_base = [k for k in before if "lora_" not in k and k in after and not torch.equal(before[k], after[k].cpu())]
    lora_keys = [k for k in after if "lora_B" in k]
    moved_lora = [k for k in lora_keys if after[k].abs().sum() > 0]
    res = {"steps": tr.state.global_step, "losses": [h["loss"] for h in logs], "n_examples": len(ex),
           "trained_tokens": sum(e.n_completion for e in ex), "masked_tokens": sum(e.n_prompt for e in ex),
           "base_weights_moved": len(moved_base), "lora_B_tensors": len(lora_keys), "lora_B_moved": len(moved_lora)}
    assert res["steps"] == 2 and all(torch.isfinite(torch.tensor(l)) for l in res["losses"]), res
    assert res["base_weights_moved"] == 0 and res["lora_B_moved"] > 0, res
    tr.model.save_pretrained(Path(out) / "adapter")
    res["adapter_saved"] = str(Path(out) / "adapter")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--data", help="golden JSONL (prompt_text/completion/prefill) built from harness runs")
    ap.add_argument("--out", default="results/sft/run")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args(argv)
    cfg = common.load_config(a.config)
    if a.smoke:
        print(json.dumps(smoke(cfg), indent=1))
        return 0
    if not a.data:
        ap.error("--data is required (or --smoke)")
    import torch
    from transformers import AutoModelForCausalLM
    name = common.policy_hf_id(cfg)
    tok = common.load_tokenizer(name)
    ex, rej = sft_data.build_examples(sft_data.load_jsonl(a.data), tok, cfg["data"]["verify_format"], cfg["data"]["max_length"])
    print(f"{len(ex)} examples, {len(rej)} rejected", file=sys.stderr)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "rejects.json").write_text(json.dumps(rej, indent=1))
    model = AutoModelForCausalLM.from_pretrained(name, dtype=torch.bfloat16 if cfg["train"].get("bf16") else None)
    tr = train(cfg, ex, model, tok, a.out)
    tr.save_model(str(Path(a.out) / "adapter"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
