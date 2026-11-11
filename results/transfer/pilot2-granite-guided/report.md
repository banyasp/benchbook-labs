# Transfer pilot: pilot2-granite-guided

604 samples, 28 X1s.

| arm | X1s | samples | accuracy (vs X1's key) | copies the case's verdict |
|---|---|---|---|---|
| no case | 28 | 112 | 53% [38-67] | — |
| own case (X2 = X1) | 28 | 112 | 96% [88-100] | — |
| transferred sister (same K) | 28 | 160 | 82% [72-91] | 82% [72-91] |
| transferred sister, flipped (verdict differs) | 20 | 108 | 29% [13-45] | 48% [30-66] |
| sister of another anchor (different K) | 28 | 112 | 47% [32-63] | — |

Paired per-X1 differences (mean over X1s present in both arms):

- transferred sister (same K) − no case: +29 points [+18, +42] (28 X1s)
- transferred sister (same K) − sister of another anchor (different K): +35 points [+23, +47] (28 X1s)
- own case (X2 = X1) − no case: +44 points [+28, +59] (28 X1s)
- transferred sister, flipped (verdict differs) − no case: -22 points [-43, -1] (20 X1s)
