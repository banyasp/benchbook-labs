# Transfer pilot: pilot1-luna

464 samples, 10 X1s.

| arm | X1s | samples | accuracy (vs X1's key) | copies the case's verdict |
|---|---|---|---|---|
| no case | 10 | 80 | 8% [0-20] | — |
| own case (X2 = X1) | 10 | 80 | 54% [32-72] | — |
| transferred sister (same K) | 10 | 128 | 41% [21-63] | 41% [21-63] |
| transferred sister, flipped (verdict differs) | 8 | 96 | 43% [20-65] | 14% [0-36] |
| sister of another anchor (different K) | 10 | 80 | 15% [0-39] | — |

Paired per-X1 differences (mean over X1s present in both arms):

- transferred sister (same K) − no case: +34 points [+18, +49] (10 X1s)
- transferred sister (same K) − sister of another anchor (different K): +26 points [+9, +44] (10 X1s)
- own case (X2 = X1) − no case: +46 points [+30, +62] (10 X1s)
- transferred sister, flipped (verdict differs) − no case: +34 points [+16, +52] (8 X1s)
