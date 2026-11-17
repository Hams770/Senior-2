# bias knobs on top of the knowledge line: bigger network, train longer (one knob per arm)

M0 at 512 tokens, CS4085 code and configuration, validation only (1,162 pairs; test never read).

| Arm | Seed | Val accuracy % | Val macro-F1 % | Val Good Fit recall % | Val Good Fit precision % | Val Potential Fit recall % | Train accuracy % | Train macro-F1 % | Train Good Fit recall % |
|---|---|---|---|---|---|---|---|---|---|
| knowledge | 42 | 57.40 | 50.66 | 36.68 | 45.49 | 36.39 70.58 | 67.83 | 84.30 |
| knowledge | 43 | 58.35 | 50.67 | 49.13 | 51.08 | 23.47 68.36 | 63.23 | 87.47 |
| knowledge | 44 | 54.39 | 42.04 | 13.49 | 34.21 | 31.29 70.90 | 69.69 | 82.75 |
| knowledge_mini | 42 | 53.01 | 46.74 | 59.17 | 33.79 | 19.39 59.24 | 55.16 | 86.09 |
| knowledge_mini | 43 | 56.97 | 48.61 | 21.11 | 44.53 | 48.30 77.25 | 76.06 | 86.17 |
| knowledge_mini | 44 | 54.73 | 45.70 | 19.72 | 35.85 | 40.48 65.69 | 61.41 | 47.36 |
| knowledge_6ep | 42 | 58.35 | 53.89 | 42.56 | 48.62 | 47.28 77.19 | 76.07 | 93.17 |
| knowledge_6ep | 43 | 60.15 | 51.33 | 55.02 | 55.59 | 18.03 66.67 | 61.33 | 84.70 |
| knowledge_6ep | 44 | 54.48 | 47.94 | 43.60 | 38.53 | 27.55 69.36 | 68.91 | 89.99 |
| **knowledge mean** | 3 | 56.71 | 47.79 | 33.10 | 43.59 | 30.39 69.94 | 66.91 | 84.84 |
| **knowledge_mini mean** | 3 | 54.91 | 47.02 | 33.33 | 38.06 | 36.05 67.39 | 64.21 | 73.20 |
| **knowledge_6ep mean** | 3 | 57.66 | 51.05 | 47.06 | 47.58 | 30.95 71.07 | 68.77 | 89.29 |

## knowledge_mini vs knowledge (seeds 42, 43, 44)

| Metric | Difference | Criterion met | Seeds better |
|---|---|---|---|
| Good Fit recall | +0.23 | False | 2/3 |
| Accuracy | -1.81 | False | 1/3 |
| Macro-F1 | -0.77 | True | 1/3 |
| Good Fit precision | -5.54 | (reported) | |

**NOT IMPROVED: criteria not met**

## knowledge_6ep vs knowledge (seeds 42, 43, 44)

| Metric | Difference | Criterion met | Seeds better |
|---|---|---|---|
| Good Fit recall | +13.96 | True | 3/3 |
| Accuracy | +0.95 | False | 3/3 |
| Macro-F1 | +3.26 | True | 3/3 |
| Good Fit precision | +3.99 | (reported) | |

**NOT IMPROVED: criteria not met**
