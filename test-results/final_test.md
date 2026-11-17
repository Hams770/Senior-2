# Final held-out test (opened once): 1759 pairs, 458 Good Fit

| Model | Accuracy % | Macro-F1 % | Good Fit recall % | Good Fit precision % | Review flag | HR reviews % | Good Fit reaching HR % |
|---|---|---|---|---|---|---|---|
| M0-256 seed 42 (platform today) | 46.33 | 37.89 | 15.07 | 19.94 | P(Good) >= 0.225 | 38.0 | 35.4 |
| M0-512 seed 42 (Mervat) | 48.04 | 41.33 | 34.28 | 32.91 | P(Good) >= 0.25 | 46.0 | 62.2 |
| M0-512 + knowledge seed 42 (final) | 49.29 | 43.21 | 39.08 | 35.24 | P(Good) >= 0.25 | 39.4 | 52.4 |

Confusion matrices (rows: true No / Potential / Good):

- M0-256 seed 42 (platform today): [[620, 87, 150], [191, 126, 127], [276, 113, 69]]
- M0-512 seed 42 (Mervat): [[591, 96, 170], [197, 97, 150], [161, 140, 157]]
- M0-512 + knowledge seed 42 (final): [[584, 103, 170], [181, 104, 159], [193, 86, 179]]
