# pytest from the repo root: make code/ importable (bench, library, harness, scorers, ...).
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "code"))
