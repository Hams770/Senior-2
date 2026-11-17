# confirmation on 8 seeds: train longer (6 epochs) on top of the knowledge line; same criteria, decision final

M0 at 512 tokens, CS4085 code and configuration, validation only (1,162 pairs; test never read).

| Arm | Seed | Val accuracy % | Val macro-F1 % | Val Good Fit recall % | Val Good Fit precision % | Val Potential Fit recall % |
|---|---|---|---|---|---|---|
| knowledge | 42 | 57.40 | 50.66 | 36.68 | 45.49 | 36.39
| knowledge | 43 | 58.35 | 50.67 | 49.13 | 51.08 | 23.47
| knowledge | 44 | 54.39 | 42.04 | 13.49 | 34.21 | 31.29
| knowledge | 45 | 56.88 | 48.77 | 33.91 | 42.98 | 31.29
| knowledge | 46 | 56.97 | 48.80 | 38.41 | 43.87 | 27.21
| knowledge | 47 | 56.54 | 49.98 | 43.94 | 42.91 | 30.27
| knowledge | 48 | 56.20 | 48.13 | 32.18 | 45.15 | 31.63
| knowledge | 49 | 57.57 | 49.64 | 47.06 | 43.59 | 23.81
| knowledge_6ep | 42 | 58.35 | 53.89 | 42.56 | 48.62 | 47.28
| knowledge_6ep | 43 | 60.15 | 51.33 | 55.02 | 55.59 | 18.03
| knowledge_6ep | 44 | 54.48 | 47.94 | 43.60 | 38.53 | 27.55
| knowledge_6ep | 45 | 56.80 | 49.06 | 32.18 | 40.97 | 35.03
| knowledge_6ep | 46 | 57.57 | 49.34 | 35.64 | 46.40 | 29.59
| knowledge_6ep | 47 | 55.59 | 49.46 | 30.45 | 41.12 | 44.90
| knowledge_6ep | 48 | 58.78 | 52.86 | 37.37 | 46.35 | 43.88
| knowledge_6ep | 49 | 58.86 | 51.82 | 36.33 | 46.26 | 37.76
| **knowledge mean** | 8 | 56.79 | 48.59 | 36.85 | 43.66 | 29.42
| **knowledge_6ep mean** | 8 | 57.57 | 50.71 | 39.14 | 45.48 | 35.50

## knowledge_6ep vs knowledge (seeds 42, 43, 44, 45, 46, 47, 48, 49)

| Metric | Difference | Criterion met | Seeds better |
|---|---|---|---|
| Good Fit recall | +2.29 | True | 4/8 |
| Accuracy | +0.79 | False | 6/8 |
| Macro-F1 | +2.12 | True | 7/8 |
| Good Fit precision | +1.82 | (reported) | |

**NOT IMPROVED: criteria not met**
