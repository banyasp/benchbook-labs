"""P3 live check: journalist (T) vs PDF REF1 (C). 1 render + 3 teacher samples (4 Bedrock calls) + projection."""
import json
from pipeline.solve.fixtures import journalist_pair, PDF
from pipeline.render import render_pair
from pipeline.solve import solve_pair
from pipeline.project import project_all
from pipeline.store import Store

root = "results/p3-livecheck/data"
st = Store(root)
if not st.pairs():
    st, pid = journalist_pair(root)
else:
    pid = "P-pdfjrn"
EQ = str(PDF / "equities.yaml")
p = st.pair(pid)
if not p.trace:
    p = render_pair(p, st)
print("render diag:", (st.pair_dir(pid) / "render.diagnostics.json").read_text())
if not p.solve:
    p = solve_pair(p, st, EQ, n=3)
for s in p.solve:
    print(s.path, s.accepted, s.reasons)
print(json.dumps(project_all(st, "v0", equities=EQ), indent=1)[:1800])
