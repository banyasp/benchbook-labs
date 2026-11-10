# Reasoning-mode comparison on transfer pilot 2

Same 28 anchors, same sisters, same traces, same equities; k=8 per cell. Granite, YAML-only (mode C): 1208 samples, Luna (hidden reasoning): 1208 samples.

## Accuracy (vs X1's key) and copy rate

| arm | Granite, YAML-only (mode C) | Luna (hidden reasoning) |
|---|---|---|
| control | 45% [32-60] | 66% [51-79] |
| self | 81% [72-88] | 91% [83-98] |
| transfer | 73% [63-83]; copies 73% | 86% [77-93]; copies 86% |
| flip | 19% [8-33]; copies 57% | 76% [61-89]; copies 14% |
| decoy | 46% [33-59] | 70% [58-81] |

## Off-menu, truncation, thinking length

| run | arm | n | off-menu | truncated | mean thinking chars |
|---|---|---|---|---|---|
| Granite, YAML-only (mode C) | control | 224 | 9% | 1% | 9,620 |
| Granite, YAML-only (mode C) | self | 224 | 8% | 8% | 13,306 |
| Granite, YAML-only (mode C) | transfer | 320 | 9% | 9% | 14,817 |
| Granite, YAML-only (mode C) | flip | 216 | 8% | 8% | 15,983 |
| Granite, YAML-only (mode C) | decoy | 224 | 17% | 4% | 14,773 |
| Luna (hidden reasoning) | control | 224 | 11% | 0% | 0 |
| Luna (hidden reasoning) | self | 224 | 3% | 0% | 0 |
| Luna (hidden reasoning) | transfer | 320 | 3% | 0% | 0 |
| Luna (hidden reasoning) | flip | 216 | 4% | 0% | 0 |
| Luna (hidden reasoning) | decoy | 224 | 6% | 0% | 0 |

## Relations declared (transfer, flip, self, decoy)

| run | arm | follows | flips | distinguished | not_governed | none |
|---|---|---|---|---|---|---|
| Granite, YAML-only (mode C) | self | 90% | 0% | 3% | 0% | 7% |
| Granite, YAML-only (mode C) | transfer | 86% | 0% | 7% | 0% | 7% |
| Granite, YAML-only (mode C) | flip | 56% | 3% | 31% | 3% | 7% |
| Granite, YAML-only (mode C) | decoy | 37% | 0% | 42% | 12% | 8% |
| Luna (hidden reasoning) | self | 93% | 0% | 5% | 0% | 1% |
| Luna (hidden reasoning) | transfer | 88% | 0% | 8% | 3% | 1% |
| Luna (hidden reasoning) | flip | 12% | 52% | 34% | 2% | 0% |
| Luna (hidden reasoning) | decoy | 0% | 0% | 0% | 97% | 3% |

## Flip arm: does the model use the flip condition?

| measure | Granite, YAML-only (mode C) | Luna (hidden reasoning) |
|---|---|---|
| flips with correct via | 3% | 52% |
| flipped cons: corresponding | 36% | 88% |
| flipped cons: matched | 27% | 1% |
| flipped cons: case_only | 22% | 9% |
| flipped cons: unmentioned | 15% | 2% |
| YAML mentions a flip condition | 18% | 45% |
| free thinking mentions a flip condition | 0% | 0% |

## Contamination: the model's OWN considerations bent toward the flipped case's verdict

Share of the reply's enumerated considerations whose `favors` includes the option the flipped sister decided (never X1's gold), on X1s that have a flip cell; mean over X1. Under no case this is the baseline; a rise under the flip arm means the model rewrote its own reading of the live facts to fit the case.

| arm | Granite, YAML-only (mode C) | Luna (hidden reasoning) |
|---|---|---|
| control | 36% (148) | 24% (158) |
| self | 19% (143) | 14% (154) |
| transfer | 23% (208) | 18% (233) |
| flip | 50% (194) | 22% (213) |
| decoy | 31% (134) | 18% (158) |

## Paired per-X1 differences between runs (same X1, same arm)

- control: Luna (hidden reasoning) − Granite, YAML-only (mode C) = +21 points [+6, +35] (28 X1s)
- self: Luna (hidden reasoning) − Granite, YAML-only (mode C) = +10 points [+3, +17] (28 X1s)
- transfer: Luna (hidden reasoning) − Granite, YAML-only (mode C) = +12 points [+4, +21] (28 X1s)
- flip: Luna (hidden reasoning) − Granite, YAML-only (mode C) = +56 points [+41, +71] (20 X1s)
- decoy: Luna (hidden reasoning) − Granite, YAML-only (mode C) = +24 points [+12, +37] (28 X1s)
