# M0 at 256 vs 512 tokens: validation only (1,162 pairs; test not opened)

| Model | Accuracy % | Macro-F1 % | Good Fit recall % | Good Fit precision % | CPU ms (model / with tokenizer) |
|---|---|---|---|---|---|
| 256_s42 | 55.59 | 46.54 | 23.88 | 46.62 | 4.4 / 9.9 |
| 256_s43 | 51.55 | 37.65 | 21.11 | 31.94 | 4.3 / 10.0 |
| 256_s44 | 50.34 | 35.86 | 5.88 | 19.77 | 4.3 / 10.0 |
| 512_s42 | 56.45 | 48.40 | 43.60 | 41.31 | 9.9 / 14.4 |
| 512_s43 | 54.91 | 43.85 | 22.84 | 37.29 | 10.0 / 14.5 |
| 512_s44 | 51.64 | 43.84 | 28.72 | 32.94 | 9.7 / 14.3 |
| 512_w1.5_s42 | 57.92 | 50.34 | 32.18 | 56.02 | 9.7 / 14.1 |
| **256 mean of 3 seeds** | 52.50 | 40.01 | 16.96 | 32.78 | |
| **512 mean of 3 seeds** | 54.33 | 45.36 | 31.72 | 37.18 | |

| Check | Result |
|---|---|
| 256_s42: SHA-256 matches | passed |
| 256_s42: reproduces the CS4085 validation result | passed |
| 256_s43: SHA-256 matches | passed |
| 256_s43: reproduces the CS4085 validation result | passed |
| 256_s44: SHA-256 matches | passed |
| 256_s44: reproduces the CS4085 validation result | passed |
| 512_s42: SHA-256 matches | passed |
| 512_s42: reproduces Mervat's confusion matrix | passed |
| 512_s43: SHA-256 matches | passed |
| 512_s43: reproduces Mervat's confusion matrix | passed |
| 512_s44: SHA-256 matches | passed |
| 512_s44: reproduces Mervat's confusion matrix | passed |
| 512_w1.5_s42: SHA-256 matches | passed |
| 512_w1.5_s42: reproduces Mervat's confusion matrix | passed |

## Good Fit review rules (mean of seeds 42, 43, 44)

| Length | Rule | Review % of applicants | Good Fit caught % (SD) | Good Fit among flagged % |
|---|---|---|---|---|
| 256 | threshold 0.100 | 58.1 | 70.2 (15.3) | 30.4 |
| 256 | threshold 0.125 | 50.5 | 65.5 (13.6) | 32.4 |
| 256 | threshold 0.150 | 45.3 | 61.7 (12.4) | 33.8 |
| 256 | threshold 0.175 | 39.5 | 55.8 (11.6) | 35.0 |
| 256 | threshold 0.200 | 35.1 | 49.8 (12.0) | 35.1 |
| 256 | threshold 0.225 | 31.4 | 44.3 (10.3) | 34.9 |
| 256 | threshold 0.250 | 27.7 | 38.5 (8.9) | 34.3 |
| 256 | threshold 0.275 | 24.0 | 33.2 (7.8) | 34.1 |
| 256 | threshold 0.300 | 21.4 | 30.1 (6.9) | 34.8 |
| 256 | threshold 0.325 | 19.2 | 26.6 (7.4) | 34.3 |
| 256 | threshold 0.350 | 17.1 | 23.8 (7.4) | 34.4 |
| 256 | threshold 0.375 | 14.8 | 20.1 (6.9) | 33.6 |
| 256 | threshold 0.400 | 12.8 | 17.1 (6.4) | 33.0 |
| 256 | threshold 0.425 | 10.8 | 13.5 (6.4) | 31.1 |
| 256 | threshold 0.450 | 8.9 | 10.6 (5.8) | 29.5 |
| 256 | threshold 0.475 | 7.3 | 7.7 (5.4) | 26.0 |
| 256 | threshold 0.500 | 5.6 | 5.2 (4.2) | 23.4 |
| 256 | top-2 | 36.4 | 45.8 (12.8) | 31.2 |
| 256 | argmax | 12.2 | 17.0 (9.7) | 32.8 |
| 512 | threshold 0.100 | 58.1 | 76.5 (15.0) | 33.2 |
| 512 | threshold 0.125 | 51.9 | 69.0 (15.7) | 33.5 |
| 512 | threshold 0.150 | 46.4 | 62.4 (16.3) | 33.9 |
| 512 | threshold 0.175 | 43.1 | 59.1 (16.8) | 34.4 |
| 512 | threshold 0.200 | 39.6 | 55.1 (15.6) | 35.0 |
| 512 | threshold 0.225 | 37.0 | 52.1 (17.1) | 35.2 |
| 512 | threshold 0.250 | 34.7 | 50.4 (17.4) | 36.2 |
| 512 | threshold 0.275 | 32.2 | 47.1 (17.2) | 36.2 |
| 512 | threshold 0.300 | 29.9 | 44.3 (15.6) | 36.8 |
| 512 | threshold 0.325 | 27.6 | 40.8 (15.3) | 36.6 |
| 512 | threshold 0.350 | 25.5 | 37.8 (13.2) | 36.8 |
| 512 | threshold 0.375 | 22.7 | 33.7 (10.4) | 36.8 |
| 512 | threshold 0.400 | 20.7 | 32.1 (9.3) | 38.6 |
| 512 | threshold 0.425 | 18.6 | 29.2 (7.3) | 39.5 |
| 512 | threshold 0.450 | 16.4 | 26.4 (5.3) | 41.0 |
| 512 | threshold 0.475 | 14.8 | 24.1 (4.1) | 42.0 |
| 512 | threshold 0.500 | 12.4 | 20.6 (3.2) | 43.9 |
| 512 | top-2 | 38.4 | 50.5 (16.1) | 34.3 |
| 512 | argmax | 21.1 | 31.7 (10.7) | 37.2 |
