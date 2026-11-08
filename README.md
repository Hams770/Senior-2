# HireMind Intelligence Platform

**AI-Assisted Recruitment with Verified Skills and HR-Led Decisions**
CS 4177 Senior Project II · Effat University · Supervisor: Dr. Fidaa Abed
Team: Hams Aljohani · Rawan Khojah · Mervat Orri

HireMind helps HR teams screen CVs for a job, verify claimed skills with short assessments, and rank
candidates with a transparent, HR-weighted score. The AI only supplies evidence: **HR makes every
decision, and the system never rejects a candidate automatically.**

## Status

| Part | Requirements | Status |
|---|---|---|
| Interface prototype (10 screens) | — | Done in Senior 1, sample data ([`frontend/`](frontend/)) |
| Login, roles, ownership checks | FR-01, FR-02, NFR-04 | **Done** (backend + tests) |
| Jobs and versioned scoring policies | FR-03, FR-04 | **Done** |
| CV upload (PDF/DOCX, ≤ 10 MB, private storage) | FR-05, FR-19 | **Done**, defects D4 and D5 fixed |
| Scoring engine | FR-10, FR-14, FR-15, NFR-08 | **Done**, defects D1, D2 and D3 fixed |
| Audit log | FR-22 | **Done** for jobs, policies, staff and applications |
| CV parser (text, sections, skills with excerpts, HR correction) | FR-06 – FR-08 | **Done** (PDF and DOCX; scanned CVs are reported, not read) |
| Fit classifier service (BERT-Tiny from CS4085) | FR-09, NFR-10 | Next, waiting for the trained weights |
| Skill assessments (MCQ graded by key, practical graded by HR rubric, time limit) | FR-11 – FR-13 | **Done** |
| Provisional and final scores, ranking with breakdown, HR decisions, hiring outcome | FR-10, FR-14 – FR-16, FR-20 | **Done** |
| Feedback drafts with HR approval | FR-17, FR-18 | Planned |
| Screens connected to the API, analytics | FR-21 | Planned |

## Run it

Requires Python 3.11 or newer.

```sh
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.cli create-admin admin@hiremind.test 'AdminPass123'
uvicorn app.main:app --reload
```

- API documentation (try every endpoint): http://127.0.0.1:8000/docs
- Interface prototype: http://127.0.0.1:8000/index.html

By default the data is stored in SQLite (`backend/hiremind.db`). To use PostgreSQL, run
`docker compose up -d` and set `DATABASE_URL` as in [`backend/.env.example`](backend/.env.example).

**Tests:** `cd backend && pytest -q`. They also run automatically on GitHub for every push, against
SQLite and PostgreSQL (see the **Actions** tab).

## How a candidate is scored

| Component | Evidence | Who provides it |
|---|---|---|
| `tech` | Share of the job's required skills found in the CV | CV parser (HR can correct) |
| `exp`, `edu`, `soft` | Experience, education, soft skills, 0-100 | HR, from the CV evidence |
| `ver` | Mean score of the assigned skill assessments | Assessments |

The score is the weighted mean of the components that have evidence, using the job's latest policy.
It is *provisional* while any weighted component is not assessed and *final* when all are present.
The fit classifier (FR-09) will be shown beside the score as extra evidence once its weights are added.

## Main API endpoints

| Method and path | Who | Purpose |
|---|---|---|
| `POST /api/auth/register` | anyone | Create a candidate account |
| `POST /api/auth/login` | anyone | Get an access token |
| `POST /api/auth/staff` | admin | Create an HR or admin account |
| `POST /api/jobs`, `PATCH /api/jobs/{id}` | HR (owner) | Create or edit a job |
| `POST /api/jobs/{id}/publish`, `/close` | HR (owner) | Open or close applications |
| `POST /api/jobs/{id}/policies` | HR (owner) | Save new scoring weights as a new version |
| `POST /api/jobs/{id}/applications` | candidate | Apply with one PDF or DOCX CV |
| `GET /api/applications/mine` | candidate | Application status |
| `GET /api/jobs/{id}/applications` | HR (owner) | Applications for a job |
| `GET /api/applications/{id}/cv` | owner HR or the candidate | Download the CV (private) |
| `GET /api/applications/{id}/parsed` | HR (owner) | Extracted text, sections and skills with their source sentence |
| `PATCH /api/applications/{id}/parsed` | HR (owner) | Correct text or skills with a reason; the parser output is kept |
| `POST /api/applications/{id}/parse` | HR (owner) | Run the parser again |
| `POST /api/jobs/{id}/assessments` | HR (owner) | Create an MCQ or practical assessment for a required skill |
| `POST /api/applications/{id}/assessments` | HR (owner) | Assign assessments to an applicant |
| `GET /api/applications/{id}/assessments` | HR (owner) or the candidate | Attempts and results (candidates never see the answer key) |
| `POST /api/attempts/{id}/start`, `/submit` | candidate | Timed attempt; late attempts are recorded as *not assessed* |
| `POST /api/attempts/{id}/grade` | HR (owner) | Grade a practical answer with its rubric |
| `PUT /api/applications/{id}/ratings` | HR (owner) | Rate experience, education and soft skills (0-100) from the CV evidence |
| `POST /api/applications/{id}/evaluate` | HR (owner) | Provisional score, or final when all evidence exists; history kept |
| `GET /api/jobs/{id}/ranking` | HR (owner) | Ranked candidates, ties share a rank, full breakdown |
| `POST /api/applications/{id}/decision` | HR (owner) | Advance, hold or reject, with a reason (never automatic) |
| `POST /api/applications/{id}/outcome` | HR (owner) | Final hiring outcome |
| `POST /api/scoring/preview` | HR | Score for given components and weights |
| `GET /api/audit` | admin | Audit log |

## Structure

```
frontend/              Senior 1 interface prototype (HTML, CSS, JavaScript)
backend/app/
  main.py              FastAPI application
  models.py            database tables (one per entity of the ERD)
  security.py          password hashing, tokens, role checks
  parser.py, skills.py CV parser and skill vocabulary
  scoring.py           scoring engine (D1-D3 fixed)
  audit.py             audit log
  routers/             auth, jobs, applications, assessments, evaluations, admin endpoints
backend/tests/         automated tests (TC-01 to TC-08, TC-10 to TC-16, TC-20, D1-D5, ST-01, NFR-08, FR-22)
docker-compose.yml     local PostgreSQL
```

## Defects from the midterm and their fixes

| ID | Defect | Fix | Test |
|---|---|---|---|
| D1 | Missing assessment counted as zero | Stored as *not assessed* and excluded; the final score needs all evidence | `test_d1_*`, `test_fr14_*` |
| D2 | Equal scores got different ranks | Ties share a rank (1, 2, 2, 4) | `test_d2_*` |
| D3 | Zero total weight gave NaN | Rejected by the server | `test_tc04_*`, `test_d3_*` |
| D4 | Analysis started without a file | Upload rejected without a non-empty file | `test_d4_*` |
| D5 | DOC files accepted | Only PDF and DOCX, checked by extension and content | `test_d5_*` |
