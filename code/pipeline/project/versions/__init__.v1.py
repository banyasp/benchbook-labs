"""project (P3, code only): PairRecord -> SFT jsonl, RLVR jsonl, Inspect samples + manifest.
CLI: python -m pipeline.project --version v0 [--all | --pair ID]"""
from .project import accepted_reply, project_all, project_pair, rl_gold, split_for_mode  # noqa: F401
