"""Cross-domain transfer sisters (Peter, 2026-11-09; plan: docs/TRANSFER-PIPELINE-PLAN-2026-11-09.md).

An anchor X1 (corpus scenario with a rendered trace) gets sisters X2 from a DIFFERENT national-security sub-domain
with the SAME considerations K. X2 is only ever served as a reference case, never rendered as a trace. Its reasoning
and verdict are transferred from X1 (one oracle: the source behind X1), never solved fresh. A flip variant X2' makes
one of the case's stated flip conditions true, so its verdict differs: copying the case's verdict is then wrong.

    sketch file (Claude subagent) --parse--> sister sketch --write (Luna)--> X2 --flip (Luna)--> X2'
    checks per X2 / X2': structure (code), answer leak (frame, facts), technique screen, blind K re-extraction + cold
    solve (agreement recorded, never used as gold), "what does this setting add" probe (strong addition -> hard case)

    PYTHONPATH=code .venv/bin/python -m pipeline.transfer --sketch <file.md> [--anchors <anchors.json>] [--limit N]

Accepted: data/store/scenarios/XFER-<anchor family>/DR-XFER-…@v1.yaml. Hard cases (the new setting adds a strong
consideration; Peter: keep them for later "notice what is different" training): data/store/transfer-hard/.
Rejected (structure, leak, technique): data/store/transfer-rejected/. Log: results/transfer/build-<date>.jsonl.
"""
