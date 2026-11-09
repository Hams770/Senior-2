# HireMind Intelligence Platform

**AI-Assisted Recruitment with Verified Skills and HR-Led Decisions**
CS 4177 Senior Project II · Effat University · Supervisor: Dr. Fidaa Abed
Team: Hams Aljohani · Rawan Khojah · Mervat Orri

HireMind helps HR teams screen CVs for a job, verify claimed skills with short assessments, and rank
candidates with a transparent, HR-weighted score. The AI only supplies evidence: **HR makes every
decision, and the system never rejects a candidate automatically.**

**The fit classifier** (No Fit / Potential Fit / Good Fit) comes from our CS4085 Deep Learning project:
[github.com/Hams770/HireMind-DL](https://github.com/Hams770/HireMind-DL). That repository holds the dataset
splits, training and evaluation code, and the held-out test results (BERT-Tiny M0: macro-F1 33.70%,
Good Fit recall 16.16%). The low Good Fit recall is why the platform flags possible Good Fit candidates for HR review
instead of letting the model decide.

## Status

| Part | Requirements | Status |
|---|---|---|
| Interface: 10 HR screens + candidate portal + sign-in, connected to the API, new visual identity | FR-19, FR-21 | **Done** ([`frontend/`](frontend/)) |
| Login, roles, ownership checks | FR-01, FR-02, NFR-04 | **Done** (backend + tests) |
| Jobs and versioned scoring policies | FR-03, FR-04 | **Done** |
| CV upload (PDF/DOCX, ≤ 10 MB, private storage) | FR-05, FR-19 | **Done**, defects D4 and D5 fixed |
| Scoring engine | FR-10, FR-14, FR-15, NFR-08 | **Done**, defects D1, D2 and D3 fixed |
| Audit log | FR-22 | **Done** for jobs, policies, staff and applications |
| CV parser (text, sections, skills with excerpts, HR correction) | FR-06 – FR-08 | **Done** (PDF and DOCX; scanned CVs are reported, not read) |
| Fit classifier service (BERT-Tiny from CS4085) | FR-09, NFR-10 | Next, waiting for the trained weights |
| Skill assessments (MCQ graded by key, practical graded by HR rubric, time limit) | FR-11 – FR-13 | **Done** |
| Provisional and final scores, ranking with breakdown, HR decisions, hiring outcome | FR-10, FR-14 – FR-16, FR-20 | **Done** |
| Feedback drafts (anonymised; LLM if a key is set, otherwise a template) released only after HR approval | FR-17, FR-18 | **Done** |
| Analytics computed only from stored records | FR-21 | **Done** |

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
- The platform: http://127.0.0.1:8000/login.html (sign in with the admin account, add an HR account in Settings, or create a candidate account on the sign-in page)

By default the data is stored in SQLite (`backend/hiremind.db`). Settings go in `backend/.env` (copy
[`backend/.env.example`](backend/.env.example); the file is never committed): `DATABASE_URL` for PostgreSQL
(`docker compose up -d` starts one), and `ANTHROPIC_API_KEY` to have feedback drafts written by the LLM instead of the template.

**Tests:** `cd backend && pytest -q` (91 tests). On every push GitHub also runs a browser test of every screen and the
non-functional tests on PostgreSQL; the screenshots and `nfr_report.md` are published to the `test-results` branch.

## Non-functional results (latest run)

| Test | Requirement | Target | Measured |
|---|---|---|---|
| PT-01 | NFR-01 | Dashboard p95 ≤ 2 s (10 users, 200 requests) | p95 0.6 s, 0 errors |
| PT-02 | NFR-02 | CV analysis p95 ≤ 120 s over 50 CVs | p95 0.11 s, 50/50 parsed (classifier not yet included) |
| PT-03 | NFR-03 | 100 simultaneous applications, none lost or duplicated | 100 stored, 100 unique |
| ST-01 | NFR-04 | No access outside role and ownership | 22 protected endpoints × anonymous / wrong role / other HR refused; forged, expired and tampered tokens refused |
| RT-01 | NFR-06 | Retries ≤ 2, invalid files rejected, data survives a restart | Passed |
| RP-01 | NFR-08 | Same inputs and policy give the same score | Passed |
| FT-01 | NFR-09 | 10 CV pairs differing in an irrelevant attribute | 0 differences in skills or score |
| UT-01 | NFR-05 | 4 of 5 users finish a task in 5 minutes, SUS reported | To do with real participants |
| AT-01 | NFR-07 | Skill extraction micro-F1 ≥ 0.85 on 30 annotated CVs | To do with real CVs |

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
| `POST /api/applications/{id}/feedback` | HR (owner) | Draft feedback from an anonymised summary |
| `POST /api/feedback/{id}/approve`, `/release` | HR (owner) | Approve (or edit) the draft, then release it |
| `GET /api/applications/{id}/feedback` | HR (owner) or the candidate | Candidates see only released feedback |
| `POST /api/scoring/preview` | HR | Score for given components and weights |
| `GET /api/audit` | admin | Audit log |

## Structure

```
frontend/              screens (HTML, CSS, JavaScript): sign-in, 10 HR screens, candidate portal
e2e/                   browser test that walks every screen and saves screenshots
nfr/                   load, concurrency and restart tests
backend/app/
  main.py              FastAPI application
  models.py            database tables (one per entity of the ERD)
  security.py          password hashing, tokens, role checks
  parser.py, skills.py CV parser and skill vocabulary
  scoring.py           scoring engine (D1-D3 fixed)
  audit.py             audit log
  feedback_writer.py   anonymised feedback drafts (LLM or template)
  routers/             auth, jobs, applications, assessments, evaluations, feedback, admin endpoints
backend/tests/         automated tests (TC-01 to TC-08, TC-10 to TC-18, TC-20, D1-D5, ST-01, NFR-08, FR-22)
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
