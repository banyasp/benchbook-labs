"""project (code only): PairRecord -> SFT jsonl, RLVR jsonl, Inspect samples + manifest.
CLI: python -m pipeline.project --version v1 --mode C"""
from .project import (accepted_reply, eval_cells, eval_rows, gold_for, pair_index, project_all, project_pair,  # noqa: F401
                      rl_gold, rl_row, sft_row, split_for_mode)
