# error analysis run: knowledge model with per-pair validation predictions

M0 at 512 tokens, CS4085 code and configuration, validation only (1,162 pairs; test never read).

| Arm | Seed | Val accuracy % | Val macro-F1 % | Val Good Fit recall % | Val Good Fit precision % | Val Potential Fit recall % |
|---|---|---|---|---|---|---|
| knowledge | 42 | 57.40 | 50.66 | 36.68 | 45.49 | 36.39
| knowledge | 43 | 58.35 | 50.67 | 49.13 | 51.08 | 23.47
| knowledge | 44 | 54.39 | 42.04 | 13.49 | 34.21 | 31.29
| knowledge | 45 | 56.88 | 48.77 | 33.91 | 42.98 | 31.29
| knowledge | 46 | 56.97 | 48.80 | 38.41 | 43.87 | 27.21
| knowledge | 47 | 56.45 | 49.86 | 43.94 | 42.91 | 29.93
| knowledge | 48 | 56.20 | 48.13 | 32.18 | 45.15 | 31.63
| knowledge | 49 | 57.57 | 49.64 | 47.06 | 43.59 | 23.81
| **knowledge mean** | 8 | 56.78 | 48.57 | 36.85 | 43.66 | 29.38
