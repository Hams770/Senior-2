# Error analysis: Good Fit misses of the knowledge model (validation, 8 seeds, 289 Good Fit pairs)

## Where the missed Good Fit go

- predicted Potential Fit: 49.3% of misses
- predicted No Fit: 50.7% of misses

## By the knowledge line

| knowledge                     |   Good Fit pairs |   share of all Good Fit % |   recall % |   share of all misses % |
|:------------------------------|-----------------:|--------------------------:|-----------:|------------------------:|
| 0 required skills found in CV |               67 |                      23.2 |       25.6 |                    28   |
| under half found              |              138 |                      47.8 |       42.6 |                    44.5 |
| half or more found            |               84 |                      29.1 |       41.7 |                    27.5 |

## By input length (CV + job tokens; everything beyond 512 is cut)

| length      |   Good Fit pairs |   share of all Good Fit % |   recall % |   share of all misses % |
|:------------|-----------------:|--------------------------:|-----------:|------------------------:|
| fits in 512 |                2 |                       0.7 |        0   |                     1.1 |
| 512-1024    |               30 |                      10.4 |       26.7 |                    12.4 |
| 1024-2048   |              184 |                      63.7 |       40.8 |                    61.1 |
| > 2048      |               73 |                      25.3 |       38   |                    25.4 |

## By how close the model was (P(Good) minus the top other class)

| margin          |   Good Fit pairs |   share of all Good Fit % |   recall % |   share of all misses % |
|:----------------|-----------------:|--------------------------:|-----------:|------------------------:|
| far (< -0.3)    |              175 |                      28.6 |          0 |                    46.5 |
| mid             |              205 |                      20.9 |          0 |                    33.9 |
| close (-0.1..0) |              143 |                      12.1 |          0 |                    19.6 |
| predicted Good  |              210 |                      38.4 |        100 |                     0   |

## Job groups with the most missed Good Fit

7 of 23 job groups with Good Fit pairs have recall 0 on every seed.

| job_group        |   Good Fit pairs |   misses (all seeds) |   recall % | title                                                                            |
|:-----------------|-----------------:|---------------------:|-----------:|:---------------------------------------------------------------------------------|
| 4a5bd7b7d234dab2 |               27 |                  200 |        7.4 | Experienced in Salesforce Industries Communications cloud.Certification a plus*1 |
| 6c1a68b3091b29e3 |               24 |                  177 |        7.8 | Your Journey at Crowe Starts Here:                                               |
| 5ebaaf46b0dec5f2 |               35 |                  173 |       38.2 | Position Title: Senior Construction Accountant (Req #: 116)                      |
| 0ffa07fa38252240 |               22 |                  147 |       16.5 | Brief Description                                                                |
| f682ef0b49385f68 |               15 |                  120 |        0   | Vaco has a client in Allentown that is looking for a Senior Accountant. We are l |
| 37e1510df017d10e |               21 |                  118 |       29.8 | Cloud and Things is a leading provider of IT solutions in the public sector. We  |
| 1e27cfc1ec405874 |               23 |                  104 |       43.5 | As a Manager, you will be a key driver in building features and platform stabili |
| 8fca2e48535b5579 |               20 |                   89 |       44.4 | Role: Senior Software Engineer                                                   |
| c40d28e6881036d2 |               17 |                   79 |       41.9 | Rightware is the company behind the Kanzi family of software tools and services  |
| c3e5cf06adeea6dc |               12 |                   77 |       19.8 | ACCOUNTANT II                                                                    |
| 1dc1417a2015b446 |               40 |                   36 |       88.8 | Centurion Consulting Group is looking for a Software Development Manager This is |
| 4858df5ec10da95b |                2 |                   16 |        0   | Electrical EngineerNDI Engineering Company is seeking an Electrical Engineer wit |

## False Good Fit

- true Potential Fit: 47.5%
- true No Fit: 52.5%

