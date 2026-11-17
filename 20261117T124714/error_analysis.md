# Error analysis: Good Fit misses of the knowledge model (validation, 8 seeds, 289 Good Fit pairs)

## Where the missed Good Fit go

- predicted Potential Fit: 53.2% of misses
- predicted No Fit: 46.8% of misses

## By the knowledge line

| knowledge                     |   Good Fit pairs |   share of all Good Fit % |   recall % |   share of all misses % |
|:------------------------------|-----------------:|--------------------------:|-----------:|------------------------:|
| no skill recognised in job    |                2 |                       0.7 |        0   |                     1.1 |
| 0 required skills found in CV |               74 |                      25.6 |       26.4 |                    29.9 |
| under half found              |              115 |                      39.8 |       45   |                    34.7 |
| half or more found            |               98 |                      33.9 |       36   |                    34.4 |

## By input length (CV + job tokens; everything beyond 512 is cut)

| length      |   Good Fit pairs |   share of all Good Fit % |   recall % |   share of all misses % |
|:------------|-----------------:|--------------------------:|-----------:|------------------------:|
| fits in 512 |                2 |                       0.7 |        0   |                     1.1 |
| 512-1024    |               30 |                      10.4 |       30   |                    11.5 |
| 1024-2048   |              184 |                      63.7 |       39.7 |                    60.8 |
| > 2048      |               73 |                      25.3 |       33.6 |                    26.6 |

## By how close the model was (P(Good) minus the top other class)

| margin          |   Good Fit pairs |   share of all Good Fit % |   recall % |   share of all misses % |
|:----------------|-----------------:|--------------------------:|-----------:|------------------------:|
| far (< -0.3)    |              196 |                      27.6 |          0 |                    43.6 |
| mid             |              206 |                      23.6 |          0 |                    37.3 |
| close (-0.1..0) |              148 |                      12   |          0 |                    19   |
| predicted Good  |              213 |                      36.9 |        100 |                     0   |

## Job groups with the most missed Good Fit

4 of 23 job groups with Good Fit pairs have recall 0 on every seed.

| job_group        |   Good Fit pairs |   misses (all seeds) |   recall % | title                                                                            |
|:-----------------|-----------------:|---------------------:|-----------:|:---------------------------------------------------------------------------------|
| 4a5bd7b7d234dab2 |               27 |                  192 |       11.1 | Experienced in Salesforce Industries Communications cloud.Certification a plus*1 |
| 6c1a68b3091b29e3 |               24 |                  188 |        2.1 | Your Journey at Crowe Starts Here:                                               |
| 5ebaaf46b0dec5f2 |               35 |                  170 |       39.3 | Position Title: Senior Construction Accountant (Req #: 116)                      |
| 0ffa07fa38252240 |               22 |                  149 |       15.3 | Brief Description                                                                |
| 1e27cfc1ec405874 |               23 |                  123 |       33.2 | As a Manager, you will be a key driver in building features and platform stabili |
| f682ef0b49385f68 |               15 |                  117 |        2.5 | Vaco has a client in Allentown that is looking for a Senior Accountant. We are l |
| 37e1510df017d10e |               21 |                  101 |       39.9 | Cloud and Things is a leading provider of IT solutions in the public sector. We  |
| c40d28e6881036d2 |               17 |                   88 |       35.3 | Rightware is the company behind the Kanzi family of software tools and services  |
| c3e5cf06adeea6dc |               12 |                   85 |       11.5 | ACCOUNTANT II                                                                    |
| 1dc1417a2015b446 |               40 |                   82 |       74.4 | Centurion Consulting Group is looking for a Software Development Manager This is |
| 8fca2e48535b5579 |               20 |                   69 |       56.9 | Role: Senior Software Engineer                                                   |
| 4858df5ec10da95b |                2 |                   16 |        0   | Electrical EngineerNDI Engineering Company is seeking an Electrical Engineer wit |

## False Good Fit

- true Potential Fit: 49.5%
- true No Fit: 50.5%

