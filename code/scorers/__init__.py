"""Benchbook scorers (2d): one function per row of the PDF v0.4 scoring table (pp. 23-24).

    from scorers import score_reply, Judge
    from scorers.judge import JevJudge, StubJudge, CachedJudge
    judge = CachedJudge(JevJudge(), path="results/judge_cache.sqlite")    # or StubJudge() offline
    scores = score_reply(parsed, key, served, judge)    # {row: float | int | None}; None = not scored

No weights across rows, no combination, no gate penalty: the reward is Peter's (TBD). See score.ROWS for the rows,
rows.py for each scorer, alignment.py for the alignment (two Choice passes, geometric mean, greedy) and the graders.
"""
from .alignment import Alignment, EnumScore, align, align_from_passes, enum_grade, set_compare, set_score
from .judge import CachedJudge, JevJudge, Judge, StubJudge
from .rows import ScoringContext, format_report
from .score import DIAGNOSTICS, ROWS, ReplyScores, score_reply, score_reply_detailed

__all__ = ["Alignment", "EnumScore", "align", "align_from_passes", "enum_grade", "set_compare", "set_score",
           "CachedJudge", "JevJudge", "Judge", "StubJudge", "ScoringContext", "format_report", "DIAGNOSTICS",
           "ROWS", "ReplyScores", "score_reply", "score_reply_detailed"]
