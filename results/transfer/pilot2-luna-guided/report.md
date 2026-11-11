# Transfer pilot: pilot2-luna-guided

1208 samples, 28 X1s.

| arm | X1s | samples | accuracy (vs X1's key) | copies the case's verdict |
|---|---|---|---|---|
| no case | 28 | 224 | 67% [55-80] | — |
| own case (X2 = X1) | 28 | 224 | 93% [84-100] | — |
| transferred sister (same K) | 28 | 320 | 88% [78-95] | 88% [78-95] |
| transferred sister, flipped (verdict differs) | 20 | 216 | 77% [62-90] | 10% [0-22] |
| sister of another anchor (different K) | 28 | 224 | 72% [57-85] | — |

Paired per-X1 differences (mean over X1s present in both arms):

- transferred sister (same K) − no case: +20 points [+10, +32] (28 X1s)
- transferred sister (same K) − sister of another anchor (different K): +15 points [+5, +27] (28 X1s)
- own case (X2 = X1) − no case: +25 points [+12, +40] (28 X1s)
- transferred sister, flipped (verdict differs) − no case: +12 points [-3, +27] (20 X1s)
