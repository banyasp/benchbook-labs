# Reasoning-mode comparison on transfer pilot 2

Same 28 anchors, same sisters, same traces, same equities; samples idx 0-0 only (partial run). Granite, YAML-only (mode C): 151 samples, Granite, think first (mode A): 151 samples, Luna (hidden reasoning): 151 samples.

## Accuracy (vs X1's key) and copy rate

| arm | Granite, YAML-only (mode C) | Granite, think first (mode A) | Luna (hidden reasoning) |
|---|---|---|---|
| control | 39% [22-59] | 54% [36-71] | 64% [46-82] |
| self | 82% [67-96] | 93% [83-100] | 93% [81-100] |
| transfer | 75% [58-91]; copies 75% | 80% [67-92]; copies 80% | 88% [74-98]; copies 88% |
| flip | 25% [10-42]; copies 60% | 38% [20-57]; copies 45% | 82% [65-95]; copies 8% |
| decoy | 50% [33-69] | 46% [30-66] | 68% [52-83] |

## Off-menu, truncation, thinking length

| run | arm | n | off-menu | truncated | mean thinking chars |
|---|---|---|---|---|---|
| Granite, YAML-only (mode C) | control | 28 | 4% | 4% | 10,983 |
| Granite, YAML-only (mode C) | self | 28 | 14% | 4% | 12,750 |
| Granite, YAML-only (mode C) | transfer | 40 | 2% | 0% | 13,993 |
| Granite, YAML-only (mode C) | flip | 27 | 4% | 7% | 15,417 |
| Granite, YAML-only (mode C) | decoy | 28 | 21% | 4% | 13,483 |
| Granite, think first (mode A) | control | 28 | 0% | 0% | 18,698 |
| Granite, think first (mode A) | self | 28 | 4% | 0% | 20,524 |
| Granite, think first (mode A) | transfer | 40 | 5% | 0% | 23,614 |
| Granite, think first (mode A) | flip | 27 | 7% | 4% | 30,424 |
| Granite, think first (mode A) | decoy | 28 | 11% | 0% | 19,864 |
| Luna (hidden reasoning) | control | 28 | 7% | 0% | 0 |
| Luna (hidden reasoning) | self | 28 | 4% | 0% | 0 |
| Luna (hidden reasoning) | transfer | 40 | 2% | 0% | 0 |
| Luna (hidden reasoning) | flip | 27 | 7% | 0% | 0 |
| Luna (hidden reasoning) | decoy | 28 | 4% | 0% | 0 |

## Relations declared (transfer, flip, self, decoy)

| run | arm | follows | flips | distinguished | not_governed | none |
|---|---|---|---|---|---|---|
| Granite, YAML-only (mode C) | self | 96% | 0% | 4% | 0% | 0% |
| Granite, YAML-only (mode C) | transfer | 82% | 0% | 10% | 0% | 8% |
| Granite, YAML-only (mode C) | flip | 48% | 0% | 41% | 4% | 7% |
| Granite, YAML-only (mode C) | decoy | 43% | 0% | 39% | 14% | 4% |
| Granite, think first (mode A) | self | 96% | 0% | 4% | 0% | 0% |
| Granite, think first (mode A) | transfer | 92% | 2% | 2% | 0% | 2% |
| Granite, think first (mode A) | flip | 44% | 15% | 37% | 0% | 4% |
| Granite, think first (mode A) | decoy | 29% | 0% | 54% | 11% | 7% |
| Luna (hidden reasoning) | self | 96% | 0% | 4% | 0% | 0% |
| Luna (hidden reasoning) | transfer | 88% | 0% | 10% | 0% | 2% |
| Luna (hidden reasoning) | flip | 11% | 48% | 37% | 4% | 0% |
| Luna (hidden reasoning) | decoy | 0% | 0% | 0% | 93% | 7% |

## Flip arm: does the model use the flip condition?

| measure | Granite, YAML-only (mode C) | Granite, think first (mode A) | Luna (hidden reasoning) |
|---|---|---|---|
| flips with correct via | 0% | 15% | 48% |
| flipped cons: corresponding | 44% | 44% | 85% |
| flipped cons: matched | 22% | 33% | 0% |
| flipped cons: case_only | 22% | 11% | 15% |
| flipped cons: unmentioned | 11% | 11% | 0% |
| YAML mentions a flip condition | 30% | 41% | 37% |
| free thinking mentions a flip condition | 0% | 63% | 0% |

## Contamination: the model's OWN considerations bent toward the flipped case's verdict

Share of the reply's enumerated considerations whose `favors` includes the option the flipped sister decided (never X1's gold), on X1s that have a flip cell; mean over X1. Under no case this is the baseline; a rise under the flip arm means the model rewrote its own reading of the live facts to fit the case.

| arm | Granite, YAML-only (mode C) | Granite, think first (mode A) | Luna (hidden reasoning) |
|---|---|---|---|
| control | 39% (19) | 28% (16) | 20% (20) |
| self | 21% (16) | 10% (20) | 14% (20) |
| transfer | 19% (27) | 20% (29) | 19% (29) |
| flip | 56% (24) | 49% (26) | 23% (27) |
| decoy | 34% (17) | 27% (18) | 19% (20) |

## Paired per-X1 differences between runs (same X1, same arm)

- control: Granite, think first (mode A) − Granite, YAML-only (mode C) = +14 points [-4, +31] (28 X1s)
- self: Granite, think first (mode A) − Granite, YAML-only (mode C) = +11 points [-3, +28] (28 X1s)
- transfer: Granite, think first (mode A) − Granite, YAML-only (mode C) = +5 points [-12, +23] (28 X1s)
- flip: Granite, think first (mode A) − Granite, YAML-only (mode C) = +12 points [-10, +35] (20 X1s)
- decoy: Granite, think first (mode A) − Granite, YAML-only (mode C) = -4 points [-24, +17] (28 X1s)
- control: Luna (hidden reasoning) − Granite, think first (mode A) = +11 points [-7, +30] (28 X1s)
- self: Luna (hidden reasoning) − Granite, think first (mode A) = +0 points [-11, +10] (28 X1s)
- transfer: Luna (hidden reasoning) − Granite, think first (mode A) = +7 points [-8, +22] (28 X1s)
- flip: Luna (hidden reasoning) − Granite, think first (mode A) = +45 points [+20, +70] (20 X1s)
- decoy: Luna (hidden reasoning) − Granite, think first (mode A) = +21 points [+4, +38] (28 X1s)
- control: Luna (hidden reasoning) − Granite, YAML-only (mode C) = +25 points [+0, +50] (28 X1s)
- self: Luna (hidden reasoning) − Granite, YAML-only (mode C) = +11 points [+0, +23] (28 X1s)
- transfer: Luna (hidden reasoning) − Granite, YAML-only (mode C) = +12 points [-9, +33] (28 X1s)
- flip: Luna (hidden reasoning) − Granite, YAML-only (mode C) = +57 points [+38, +78] (20 X1s)
- decoy: Luna (hidden reasoning) − Granite, YAML-only (mode C) = +18 points [-4, +39] (28 X1s)
