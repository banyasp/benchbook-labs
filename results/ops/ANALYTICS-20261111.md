# Operator pipeline analytics

Read-only (`python -m pipeline.ops analytics`). Drift metrics are over accepted outputs. Nothing here deletes data.

| op/mode | accepted | hard | rejected | gate failures | verdict_shift flag / informative / run |
|---|---|---|---|---|---|
| judgment_edit | 66 | 0 | 0 | - | 0 / 0 / 0 |
| permute | 13 | 0 | 0 | - | 0 / 0 / 0 |
| structural_edit/flip | 106 | 0 | 0 | - | 0 / 0 / 0 |
| structural_edit/target_f | 45 | 0 | 0 | - | 0 / 0 / 0 |
| surface_edit/reword | 78 | 0 | 0 | - | 0 / 0 / 0 |
| surface_edit/transfer | 63 | 0 | 0 | - | 0 / 0 / 0 |

## Drift over accepted outputs

| op/mode | n | gold position (per option count) | option length spread (median) | gold is longest | facts supporting gold vs others (mean) | hand-up golds | facts / considerations (mean) | tiers |
|---|---|---|---|---|---|---|---|---|
| judgment_edit | 66 | 2-opt: 1:8 2:5; 3-opt: 1:7 2:4 3:10; 4-opt: 1:13 2:8 3:6 4:5 | 1.20 | 40/66 | 3.1 vs 3.1 | 18/66 | 8.0 / 4.7 | by-construction 66 |
| permute | 13 | 3-opt: 1:1 2:5; 4-opt: 1:4 2:1 3:2 | 1.22 | 6/13 | 6.7 vs 1.5 | 3/13 | 8.8 / 4.2 | by-construction 4, model-solved 2, source-endorsed 7 |
| structural_edit/flip | 106 | 2-opt: 1:21 2:18; 3-opt: 1:12 2:14 3:12; 4-opt: 1:6 2:8 3:9 4:6 | 1.14 | 51/106 | 6.2 vs 1.5 | 7/106 | 8.4 / 3.6 | by-construction 106 |
| structural_edit/target_f | 45 | 2-opt: 1:4 2:6; 3-opt: 1:2 2:3 3:7; 4-opt: 1:5 2:8 3:4 4:6 | 1.13 | 26/45 | 9.1 vs 0.4 | 4/45 | 8.8 / 4.8 | model-solved 45 |
| surface_edit/reword | 78 | 2-opt: 1:5 2:10; 3-opt: 1:7 2:10 3:6; 4-opt: 1:10 2:10 3:7 4:13 | 1.12 | 42/78 | 8.2 vs 0.1 | 2/78 | 7.9 / 4.3 | by-construction 78 |
| surface_edit/transfer | 63 | 2-opt: 1:19 2:15; 3-opt: 1:9 2:12 3:8 | 1.17 | 47/63 | 6.7 vs 1.2 | 1/63 | 7.8 / 3.5 | by-construction 63 |
