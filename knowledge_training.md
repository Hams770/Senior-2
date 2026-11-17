# Knowledge line vs matched control: M0/512, validation only (1,162 pairs; test not read)

Same CS4085 code and frozen configuration, trained on CPU in CI. Only difference: the knowledge line in front of the job text.

| Variant | Seed | Accuracy % | Macro-F1 % | Good Fit recall % | Good Fit precision % | Potential Fit recall % | Best step |
|---|---|---|---|---|---|---|---|
| control | 42 | 55.42 | 45.23 | 21.80 | 39.13 | 31.97 | 939 |
| control | 43 | 54.82 | 42.92 | 21.45 | 43.36 | 23.13 | 939 |
| control | 44 | 52.24 | 42.50 | 24.57 | 33.81 | 24.83 | 700 |
| knowledge | 42 | 57.40 | 50.66 | 36.68 | 45.49 | 36.39 | 939 |
| knowledge | 43 | 58.35 | 50.67 | 49.13 | 51.08 | 23.47 | 939 |
| knowledge | 44 | 54.39 | 42.04 | 13.49 | 34.21 | 31.29 | 800 |
| **control mean** | | 54.16 | 43.55 | 22.61 | 38.77 | 26.64 | |
| **knowledge mean** | | 56.71 | 47.79 | 33.10 | 43.59 | 30.39 | |

| Difference (knowledge - control) | Value | Criterion met |
|---|---|---|
| Good Fit recall | +10.50 | True |
| Accuracy | +2.55 | True |
| Macro-F1 | +4.24 | True |
| Good Fit precision | +4.83 | (reported) |

**Verdict: PROMISING, all criteria met** (n = 6 runs)
