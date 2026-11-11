# Transfer pilot: pilot2-luna-free

1208 samples, 28 X1s.

| arm | X1s | samples | accuracy (vs X1's key) | copies the case's verdict |
|---|---|---|---|---|
| no case | 28 | 224 | 73% [59-86] | — |
| own case (X2 = X1) | 28 | 224 | 95% [87-100] | — |
| transferred sister (same K) | 28 | 320 | 93% [84-99] | 93% [84-99] |
| transferred sister, flipped (verdict differs) | 20 | 216 | 70% [51-87] | 11% [1-25] |
| sister of another anchor (different K) | 28 | 224 | 71% [58-85] | — |

Paired per-X1 differences (mean over X1s present in both arms):

- transferred sister (same K) − no case: +20 points [+9, +32] (28 X1s)
- transferred sister (same K) − sister of another anchor (different K): +22 points [+9, +35] (28 X1s)
- own case (X2 = X1) − no case: +22 points [+11, +33] (28 X1s)
- transferred sister, flipped (verdict differs) − no case: +2 points [-14, +16] (20 X1s)
