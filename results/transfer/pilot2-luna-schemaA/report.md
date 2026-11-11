# Transfer pilot: pilot2-luna-schemaA

1208 samples, 28 X1s.

| arm | X1s | samples | accuracy (vs X1's key) | copies the case's verdict |
|---|---|---|---|---|
| no case | 28 | 224 | 71% [56-85] | — |
| own case (X2 = X1) | 28 | 224 | 94% [88-99] | — |
| transferred sister (same K) | 28 | 320 | 88% [79-96] | 88% [79-96] |
| transferred sister, flipped (verdict differs) | 20 | 216 | 80% [68-91] | 11% [2-24] |
| sister of another anchor (different K) | 28 | 224 | 75% [63-87] | — |

Paired per-X1 differences (mean over X1s present in both arms):

- transferred sister (same K) − no case: +17 points [+6, +32] (28 X1s)
- transferred sister (same K) − sister of another anchor (different K): +13 points [+4, +24] (28 X1s)
- own case (X2 = X1) − no case: +23 points [+11, +38] (28 X1s)
- transferred sister, flipped (verdict differs) − no case: +13 points [-3, +30] (20 X1s)
