# Transfer pilot: pilot1

464 samples, 10 X1s.

| arm | X1s | samples | accuracy (vs X1's key) | copies the case's verdict |
|---|---|---|---|---|
| no case | 10 | 80 | 8% [0-16] | — |
| own case (X2 = X1) | 10 | 80 | 89% [78-99] | — |
| transferred sister (same K) | 10 | 128 | 58% [42-72] | 58% [42-72] |
| transferred sister, flipped (verdict differs) | 8 | 96 | 5% [0-11] | 62% [45-78] |
| sister of another anchor (different K) | 10 | 80 | 14% [4-25] | — |

Paired per-X1 differences (mean over X1s present in both arms):

- transferred sister (same K) − no case: +51 points [+36, +65] (10 X1s)
- transferred sister (same K) − sister of another anchor (different K): +44 points [+27, +62] (10 X1s)
- own case (X2 = X1) − no case: +81 points [+71, +91] (10 X1s)
- transferred sister, flipped (verdict differs) − no case: -5 points [-17, +5] (8 X1s)
