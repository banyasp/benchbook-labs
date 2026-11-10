# Transfer pilot: pilot2

1208 samples, 28 X1s.

| arm | X1s | samples | accuracy (vs X1's key) | copies the case's verdict |
|---|---|---|---|---|
| no case | 28 | 224 | 45% [32-60] | — |
| own case (X2 = X1) | 28 | 224 | 81% [72-88] | — |
| transferred sister (same K) | 28 | 320 | 73% [63-83] | 73% [63-83] |
| transferred sister, flipped (verdict differs) | 20 | 216 | 19% [8-33] | 57% [42-72] |
| sister of another anchor (different K) | 28 | 224 | 46% [33-59] | — |

Paired per-X1 differences (mean over X1s present in both arms):

- transferred sister (same K) − no case: +28 points [+15, +41] (28 X1s)
- transferred sister (same K) − sister of another anchor (different K): +28 points [+14, +41] (28 X1s)
- own case (X2 = X1) − no case: +36 points [+22, +50] (28 X1s)
- transferred sister, flipped (verdict differs) − no case: -24 points [-37, -11] (20 X1s)
