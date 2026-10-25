"""Shared loader: imports the pilot's own run_heldout loaders, backed by the copied solver_v2."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PILOT = os.path.abspath(os.path.join(HERE, "../../src/data-scaling-v1/pilot-unzipped/pilot"))
sys.path.insert(0, HERE)            # solver_v2 copy
sys.path.insert(1, PILOT)
import run_heldout as RH            # noqa: E402  (pilot code, unmodified)
def load(with_doctrine=False):
    cat, default = RH.load_catalog(with_doctrine)
    cases = RH.load_cases(cat)
    return cat, default, cases
