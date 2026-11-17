# diagnose: bias or variance (Orthogonalization, CS4085 Chapter 4)

M0 at 512 tokens, CS4085 code and configuration, validation only (1,162 pairs; test never read).

| Arm | Seed | Val accuracy % | Val macro-F1 % | Val Good Fit recall % | Val Good Fit precision % | Val Potential Fit recall % | Train accuracy % | Train macro-F1 % | Train Good Fit recall % |
|---|---|---|---|---|---|---|---|---|---|
| control | 42 | 55.42 | 45.23 | 21.80 | 39.13 | 31.97 71.40 | 69.34 | 86.74 |
| control | 43 | 54.82 | 42.92 | 21.45 | 43.36 | 23.13 70.46 | 66.74 | 89.34 |
| control | 44 | 52.24 | 42.50 | 24.57 | 33.81 | 24.83 67.19 | 66.62 | 80.72 |
| knowledge | 42 | 57.40 | 50.66 | 36.68 | 45.49 | 36.39 70.56 | 67.80 | 84.13 |
| knowledge | 43 | 58.35 | 50.67 | 49.13 | 51.08 | 23.47 68.36 | 63.23 | 87.47 |
| knowledge | 44 | 54.39 | 42.04 | 13.49 | 34.21 | 31.29 70.90 | 69.69 | 82.75 |
| **control mean** | 3 | 54.16 | 43.55 | 22.61 | 38.77 | 26.64 69.68 | 67.57 | 85.60 |
| **knowledge mean** | 3 | 56.71 | 47.79 | 33.10 | 43.59 | 30.39 69.94 | 66.91 | 84.78 |

## knowledge vs control (seeds 42, 43, 44)

| Metric | Difference | Criterion met | Seeds better |
|---|---|---|---|
| Good Fit recall | +10.50 | True | 2/3 |
| Accuracy | +2.55 | True | 3/3 |
| Macro-F1 | +4.24 | True | 2/3 |
| Good Fit precision | +4.83 | (reported) | |

**PROMISING: all criteria met**
