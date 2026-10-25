"""solve (P3): the teacher writes the reply given the full gold structure; accept iff it matches gold.
CLI: python -m pipeline.solve --pair ID | --all"""
from .check import check_reply, clean_reply  # noqa: F401
from .episode import load_equities, student_episode  # noqa: F401
from .solve import acceptance_report, gold_brief, solve_pair, teacher_messages  # noqa: F401
from .structure import GoldStructure  # noqa: F401
