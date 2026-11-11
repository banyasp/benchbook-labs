# Transfer pilot: pilot2-granite-free

604 samples, 28 X1s.

| arm | X1s | samples | accuracy (vs X1's key) | copies the case's verdict |
|---|---|---|---|---|
| no case | 28 | 112 | 50% [35-66] | — |
| own case (X2 = X1) | 28 | 112 | 95% [87-100] | — |
| transferred sister (same K) | 28 | 160 | 81% [68-92] | 81% [68-92] |
| transferred sister, flipped (verdict differs) | 20 | 108 | 28% [12-46] | 49% [31-66] |
| sister of another anchor (different K) | 28 | 112 | 50% [34-66] | — |

Paired per-X1 differences (mean over X1s present in both arms):

- transferred sister (same K) − no case: +31 points [+20, +42] (28 X1s)
- transferred sister (same K) − sister of another anchor (different K): +31 points [+19, +42] (28 X1s)
- own case (X2 = X1) − no case: +45 points [+29, +59] (28 X1s)
- transferred sister, flipped (verdict differs) − no case: -21 points [-41, -1] (20 X1s)
