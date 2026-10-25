"""render (P3): T Scenario -> trace.json + SpanMap. CLI: python -m pipeline.render --pair ID | --all"""
from .render import (INJECTION, RenderError, build_messages, find_quote, locate, render_pair,  # noqa: F401
                     render_trace)
