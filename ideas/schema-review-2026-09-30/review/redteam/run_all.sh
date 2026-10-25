#!/usr/bin/env bash
# Re-runs every red-team probe and writes outputs.txt. solver_v2.py and reward.py are verbatim copies of src/schema/.
set -e
cd "$(dirname "$0")"
cmp -s solver_v2.py ../../src/schema/solver_v2.py && cmp -s reward.py ../../src/schema/reward.py && echo "copies match src/schema" > outputs.txt
for s in rt_solver.py rt_reward.py rt_doha.py rt_shortcuts_hardcalls.py rt_hardcalls_structure.py rt_fuzz_monotone.py rt_doha_fix.py; do
  echo -e "\n\n######## $s ########" >> outputs.txt
  python3 "$s" >> outputs.txt 2>&1
done
echo "wrote outputs.txt"
