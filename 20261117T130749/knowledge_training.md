# knowledge v2 (non-technical domains added to the vocabulary) vs knowledge v1; 8 seeds, same pre-set criteria

M0 at 512 tokens, CS4085 code and configuration, validation only (1,162 pairs; test never read).

| Arm | Seed | Val accuracy % | Val macro-F1 % | Val Good Fit recall % | Val Good Fit precision % | Val Potential Fit recall % |
|---|---|---|---|---|---|---|
| knowledge | 42 | 57.40 | 50.66 | 36.68 | 45.49 | 36.39
| knowledge | 43 | 58.35 | 50.67 | 49.13 | 51.08 | 23.47
| knowledge | 44 | 54.39 | 42.04 | 13.49 | 34.21 | 31.29
| knowledge | 45 | 56.88 | 48.97 | 32.87 | 43.18 | 33.33
| knowledge | 46 | 56.97 | 48.80 | 38.41 | 43.87 | 27.21
| knowledge | 47 | 56.54 | 49.98 | 43.94 | 42.91 | 30.27
| knowledge | 48 | 56.20 | 48.13 | 32.18 | 45.15 | 31.63
| knowledge | 49 | 57.57 | 49.64 | 47.06 | 43.59 | 23.81
| knowledge_v2 | 42 | 54.56 | 46.15 | 26.64 | 38.31 | 33.33
| knowledge_v2 | 43 | 59.12 | 53.69 | 47.40 | 53.52 | 35.71
| knowledge_v2 | 44 | 53.96 | 44.49 | 23.53 | 34.34 | 30.27
| knowledge_v2 | 45 | 55.85 | 47.37 | 40.83 | 41.26 | 22.79
| knowledge_v2 | 46 | 57.83 | 49.80 | 45.33 | 45.80 | 24.15
| knowledge_v2 | 47 | 53.01 | 44.75 | 33.22 | 36.09 | 24.83
| knowledge_v2 | 48 | 58.09 | 50.09 | 36.68 | 52.74 | 29.93
| knowledge_v2 | 49 | 59.04 | 52.20 | 53.29 | 45.70 | 26.87
| **knowledge mean** | 8 | 56.79 | 48.61 | 36.72 | 43.68 | 29.68
| **knowledge_v2 mean** | 8 | 56.43 | 48.57 | 38.37 | 43.47 | 28.49

## knowledge_v2 vs knowledge (seeds 42, 43, 44, 45, 46, 47, 48, 49)

| Metric | Difference | Criterion met | Seeds better |
|---|---|---|---|
| Good Fit recall | +1.64 | False | 5/8 |
| Accuracy | -0.35 | False | 4/8 |
| Macro-F1 | -0.05 | True | 5/8 |
| Good Fit precision | -0.22 | (reported) | |

**NOT IMPROVED: criteria not met**
