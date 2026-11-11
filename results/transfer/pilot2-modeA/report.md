# Transfer pilot: pilot2-modeA

1208 samples, 28 X1s.

| arm | X1s | samples | accuracy (vs X1's key) | copies the case's verdict |
|---|---|---|---|---|
| no case | 28 | 224 | 48% [35-61] | — |
| own case (X2 = X1) | 28 | 224 | 90% [82-97] | — |
| transferred sister (same K) | 28 | 320 | 81% [72-89] | 81% [72-89] |
| transferred sister, flipped (verdict differs) | 20 | 216 | 31% [16-48] | 49% [31-67] |
| sister of another anchor (different K) | 28 | 224 | 48% [34-64] | — |

Paired per-X1 differences (mean over X1s present in both arms):

- transferred sister (same K) − no case: +33 points [+22, +44] (28 X1s)
- transferred sister (same K) − sister of another anchor (different K): +33 points [+20, +46] (28 X1s)
- own case (X2 = X1) − no case: +42 points [+28, +56] (28 X1s)
- transferred sister, flipped (verdict differs) − no case: -14 points [-28, -1] (20 X1s)
