"""Export the store to data/exports/<version>/{sft,rl,eval}.

    PYTHONPATH=code .venv/bin/python -m pipeline.project --version v1 --mode C [--max-length 28000]

--mode is required (B, C, Cprime): there is no default. SFT uses C.
"""
import argparse
import json
import sys

from pipeline.store import DATA, Store

from . import project_all


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pipeline.project")
    ap.add_argument("--version", required=True)
    ap.add_argument("--mode", required=True, choices=["B", "C", "Cprime"], help="reasoning mode; required, no default (SFT: C)")
    ap.add_argument("--pair", action="append", help="only these pairs (repeatable); default: all pairs in the store")
    ap.add_argument("--data", default=str(DATA))
    ap.add_argument("--writers", nargs="*", default=["granite-rs"], help="writers kept in sft/rl (default granite-rs; "
                    "pass `teacher` to include the alternative writer; empty list = all)")
    ap.add_argument("--eval-cells", choices=["core", "all"], default="all", help="core = AR on/full/E_d on; all adds ar_off, thin, eq_off")
    ap.add_argument("--max-length", type=int, help="tokenize and log SFT rows that exceed this many tokens (rows stay in the export)")
    a = ap.parse_args(argv)
    st = Store(a.data)
    pairs = [st.pair(p) for p in a.pair] if a.pair else None
    m = project_all(st, a.version, pairs, mode=a.mode, writers=tuple(a.writers), eval_cells_=a.eval_cells,
                    max_length=a.max_length)
    print(json.dumps({k: m[k] for k in ("version", "mode", "counts", "skipped", "by_arm", "by_card_view", "by_intent",
                                        "eval_by_cell", "thin_leaks", "max_length_report", "files")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
