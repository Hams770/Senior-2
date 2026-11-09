"""Prepare the platform for the usability test (UT-01 / NFR-05).

Server must be running (uvicorn app.main:app) with an admin account. For each participant P1..P5 this creates
an HR account with one published job, three applicants (parsed CVs, one graded MCQ each), so task 3 has data.
It also writes sample_cv.pdf for task 2.

    python evaluation/ut01_usability/seed_usability.py --admin admin@hiremind.test --password 'AdminPass123'
"""
import argparse
import io
import sys
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend" / "tests"))
from cvfiles import CV_LINES, make_docx, make_pdf  # noqa: E402

PEOPLE = [("Sara Ahmed", CV_LINES),
          ("Lama Saeed", CV_LINES[:9] + ["Skills", "SQL, Excel, Java", "Teamwork and communication"]),
          ("Dana Khalid", CV_LINES[:6] + ["Education", "BSc Information Systems, 2024", "Skills", "Python, Power BI, Git"])]
MCQ = {"skill": "sql", "type": "mcq", "title": "SQL basics", "time_limit_min": 10, "questions": [
    {"text": "Which clause filters groups after GROUP BY?", "options": ["WHERE", "HAVING", "ORDER BY"], "answer": 1},
    {"text": "Which join keeps every row of the left table?", "options": ["INNER JOIN", "LEFT JOIN"], "answer": 1}]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--admin", required=True)
    ap.add_argument("--password", required=True)
    a = ap.parse_args()
    c = httpx.Client(base_url=a.base, timeout=60)

    def login(email, pw):
        r = c.post("/api/auth/login", data={"username": email, "password": pw})
        r.raise_for_status()
        return {"Authorization": "Bearer " + r.json()["access_token"]}

    admin = login(a.admin, a.password)
    rows = []
    for p in range(1, 6):
        email, pw = f"hr.p{p}@usability.test", f"Usability{p}23"
        r = c.post("/api/auth/staff", headers=admin, json={"email": email, "password": pw, "full_name": f"HR participant {p}", "role": "hr"})
        if r.status_code not in (201, 409):
            r.raise_for_status()
        hr = login(email, pw)
        jid = c.post("/api/jobs", headers=hr, json={"title": "Data Analyst", "level": "Junior",
            "description": "Turn sales data into weekly reports and dashboards for store managers.",
            "required_skills": ["sql", "python", "power bi"]}).json()["id"]
        c.post(f"/api/jobs/{jid}/publish", headers=hr).raise_for_status()
        mcq = c.post(f"/api/jobs/{jid}/assessments", headers=hr, json=MCQ).json()["id"]
        for i, (name, lines) in enumerate(PEOPLE):
            cand_email = f"applicant{i}.p{p}@usability.test"
            c.post("/api/auth/register", json={"email": cand_email, "password": "Applicant123", "full_name": name})
            h = login(cand_email, "Applicant123")
            app_id = c.post(f"/api/jobs/{jid}/applications", headers=h,
                            files={"cv": ("cv.docx", io.BytesIO(make_docx([name] + lines[1:])))}).json()["id"]
            tid = c.post(f"/api/applications/{app_id}/assessments", headers=hr, json={"assessment_ids": [mcq]}).json()[0]["id"]
            c.post(f"/api/attempts/{tid}/start", headers=h)
            c.post(f"/api/attempts/{tid}/submit", headers=h, json={"answers": [1, i % 2]})
        rows.append((p, email, pw))
    (HERE / "sample_cv.pdf").write_bytes(make_pdf(["Noor Hassan"] + CV_LINES[1:]))
    print("Accounts for the test (give each participant only their own):")
    for p, email, pw in rows:
        print(f"  P{p}: {email} / {pw}")
    print("Task 2 CV file:", HERE / "sample_cv.pdf")


if __name__ == "__main__":
    main()
