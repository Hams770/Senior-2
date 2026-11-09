# UT-01 usability test (NFR-05)

**Target (midterm report):** four of five users finish a task within five minutes, and the SUS score is reported.
Five participants who are not on the team, three tasks each, about 15 minutes per person.

## Before the sessions
1. Start the platform on the laptop used for the test (see the main README) with an admin account.
2. Run `python evaluation/ut01_usability/seed_usability.py --admin <admin email> --password <admin password>`.
   It creates one HR account per participant (P1–P5), each with a published job and three applicants, and
   writes `sample_cv.pdf` for task 2. Note the accounts it prints.
3. Print or open: `tasks.md` (read the tasks aloud), `consent.md`, and `UT-01_results.xlsx`.

## During each session
- Read the consent text and get a yes. Explain that the platform is being tested, not them.
- Read one task at a time and start a timer. **Do not help or hint.** If they ask, say "do what you think is right".
- Stop the timer when the success condition in `tasks.md` is met, or at 5 minutes (record "No").
- Note where they hesitated or made an error.
- After the three tasks, they fill in the 10 SUS statements (1 = strongly disagree, 5 = strongly agree).

## Recording
Type times, completion and SUS answers into `UT-01_results.xlsx`. The **Summary** sheet calculates each task's
completion count, whether NFR-05 is met (at least 4 of 5 within 5 minutes) and the mean SUS score (0–100; 68 is
a commonly cited average). Report the numbers and the main problems observed in the final report.
