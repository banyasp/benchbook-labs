"""Shared fixtures for the scorer tests: the PDF journalist example (code/bench/fixtures/pdf_example)."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from bench.schema import AnswerKey, Case, parse_reply

ROOT = Path(__file__).resolve().parents[3]
PDF = ROOT / "code" / "bench" / "fixtures" / "pdf_example"
SMOKE = ROOT / "results" / "smoke" / "INT-301-v01.think.reply.yaml"


def reply_text() -> str:
    return (PDF / "journalist.reply.yaml").read_text()


def reply_docs() -> list[dict]:
    return [d for d in yaml.safe_load_all(reply_text()) if d]


class _Indented(yaml.SafeDumper):
    """Indent block lists under their key. Needed because bench.schema.parse_reply ends a document at the first
    column-0 line that is not `key:` -- which includes PyYAML's default `- item` list style (reported to 2a)."""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def dump_docs(docs: list[dict]) -> str:
    return "\n---\n".join(yaml.dump(d, Dumper=_Indented, sort_keys=False, allow_unicode=True, width=200)
                          for d in docs)


def key_dict() -> dict:
    return yaml.safe_load((PDF / "journalist.answer_key.yaml").read_text())


def full_key_dict() -> dict:
    """The fixture key lacks the gold fact and consideration lists (2a gap); fill them from the PDF reply itself,
    which *is* the gold (pp. 14-18), so every row of the table has gold."""
    k = key_dict()
    docs = {d["kind"]: d for d in reply_docs()}
    k["facts"] = copy.deepcopy(docs["fact_enumeration"]["facts"])
    k["considerations"] = copy.deepcopy(docs["consideration_enumeration"]["considerations"])
    return k


@pytest.fixture
def case():
    return Case.load(PDF / "REF1.case.yaml")


@pytest.fixture
def served(case):
    return case.serve("REF1")


@pytest.fixture
def key():
    return AnswerKey.model_validate(full_key_dict())


@pytest.fixture
def parsed():
    return parse_reply(reply_text())
