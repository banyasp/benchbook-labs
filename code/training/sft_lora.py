"""LoRA SFT with PEFT + TRL SFTTrainer on pre-masked examples from training.sft_data.

    # real run (GPU): STOP vLLM first (bash code/inference/serve.sh --stop); both need the 48 GB.
    PYTHONPATH=code python -m training.sft_lora --data data/exports/v1/sft/sft.jsonl --out results/sft/run1
    # then serve the adapter: LORA=results/sft/run1/adapter bash code/inference/serve.sh
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

DEFAULT_CONFIG = common.HERE / "configs" / "sft_lora.v2-mode-c-v1-export.yaml"


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
    data = a.data or cfg["data"].get("path")
    if not data:
        ap.error("--data is required (or --smoke)")
    import torch
    from transformers import AutoModelForCausalLM
    name = common.policy_hf_id(cfg)
    tok = common.load_tokenizer(name)
    recs = sft_data.load_jsonl(data)
    need = cfg["data"].get("require_mode")
    if need:
        wrong = sorted({(r.get("meta") or {}).get("mode") for r in recs} - {need})
        if wrong:
            raise SystemExit(f"{data} has rows in mode(s) {wrong}; this config trains mode {need} only "
                             f"(re-export with `python -m pipeline.project --mode {need}`)")
    max_len = cfg["data"]["max_length"]
    ex, rej = sft_data.build_examples(recs, tok, cfg["data"]["verify_format"], max_len)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "rejects.json").write_text(json.dumps(rej, indent=1))
    drops = sft_data.report_drops(rej, len(recs), max_len)          # explicit, logged: never a silent drop
    (Path(a.out) / "dropped_max_length.json").write_text(json.dumps(drops, indent=1))
    fmt = [r for r in rej if r.get("dropped") != "max_length"]
    print(f"{len(ex)} examples kept of {len(recs)}; {len(drops['ids'])} dropped for length, {len(fmt)} for format/mask",
          file=sys.stderr)
    if len(recs) and drops["share"] > cfg["data"].get("drop_report_share_fail", 1.0):
        raise SystemExit(f"{drops['share']:.0%} of rows exceed max_length {max_len}; see {a.out}/dropped_max_length.json")
    if not ex:
        raise SystemExit("no trainable examples")
    print(f"mean prompt tokens {sum(e.n_prompt for e in ex) / len(ex):.0f}, mean reply tokens {sum(e.n_completion for e in ex) / len(ex):.0f}, "
          f"max total {max(len(e.input_ids) for e in ex)}", file=sys.stderr)
    kw = {"dtype": torch.bfloat16 if cfg["train"].get("bf16") else None}
    if (cfg.get("model") or {}).get("attn_implementation"):
        kw["attn_implementation"] = cfg["model"]["attn_implementation"]
    model = AutoModelForCausalLM.from_pretrained(name, **kw)
    tr = train(cfg, ex, model, tok, a.out)
    tr.save_model(str(Path(a.out) / "adapter"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
