"""render (W5): T Scenario -> TraceRecord in the trace store (v3), plus the legacy per-pair v2 path.
CLI: python -m pipeline.render --trace-scenario ID | --all-needed   (legacy: --pair ID | --all)"""
from .render import (INJECTION, RenderError, build_messages, find_quote, locate, render_pair,  # noqa: F401
                     render_trace)
from .trace import (cards_for, needed, render_many, render_one, render_trace_v3)  # noqa: F401
