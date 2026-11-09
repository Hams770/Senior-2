"""End-to-end check of the connected screens in a real browser (run by CI).

Starts from an empty database with the server on :8000, seeds data through the API, then walks every
screen as HR and as a candidate, saving a screenshot of each. Fails on any browser error or failed request.
    python e2e/run_e2e.py   (needs: pip install playwright httpx; playwright install chromium)
"""
import io
import sys
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "tests"))
from cvfiles import CV_LINES, make_docx, make_pdf, scanned_pdf  # noqa: E402

BASE = "http://127.0.0.1:8000"
OUT = ROOT / "test-results" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
problems = []


def login(c, email, pw):
    r = c.post("/api/auth/login", data={"username": email, "password": pw})
    r.raise_for_status()
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def seed():
    c = httpx.Client(base_url=BASE, timeout=30)
    admin = login(c, "admin@hiremind.test", "AdminPass123")
    c.post("/api/auth/staff", headers=admin, json={"email": "noura@hiremind.test", "password": "HrPass1234",
                                                   "full_name": "Noura Al-Harbi", "role": "hr"}).raise_for_status()
    hr = login(c, "noura@hiremind.test", "HrPass1234")
    jid = c.post("/api/jobs", headers=hr, json={"title": "Data Analyst", "level": "Junior",
        "description": "Turn sales data into weekly reports and dashboards for store managers.",
        "required_skills": ["sql", "python", "power bi", "java"], "deadline": "2026-12-15T23:59:00Z"}).json()["id"]
    c.post(f"/api/jobs/{jid}/publish", headers=hr).raise_for_status()
    j2 = c.post("/api/jobs", headers=hr, json={"title": "Junior Backend Developer", "level": "Junior",
        "description": "Build and test REST APIs for our internal tools.", "required_skills": ["python", "fastapi", "postgresql"]}).json()["id"]
    c.post(f"/api/jobs/{j2}/publish", headers=hr)
    c.post("/api/jobs", headers=hr, json={"title": "UX Designer", "description": "Design screens for the HR portal.",
                                          "required_skills": ["figma", "ui/ux"]})
    mcq = c.post(f"/api/jobs/{jid}/assessments", headers=hr, json={"skill": "sql", "type": "mcq", "title": "SQL basics", "time_limit_min": 10,
        "questions": [{"text": "Which clause filters groups after GROUP BY?", "options": ["WHERE", "HAVING", "ORDER BY"], "answer": 1},
                      {"text": "Which join keeps every row of the left table?", "options": ["INNER JOIN", "LEFT JOIN"], "answer": 1}]}).json()["id"]
    prac = c.post(f"/api/jobs/{jid}/assessments", headers=hr, json={"skill": "python", "type": "practical", "title": "Clean a customer list",
        "time_limit_min": 20, "prompt": "Explain how you would remove duplicate customers from a CSV file of 50,000 rows.",
        "rubric": [{"criterion": "Correct approach", "max_points": 6}, {"criterion": "Clear explanation", "max_points": 4}]}).json()["id"]
    people = [("Sara Ahmed", "sara@example.com", "cv.docx", make_docx()),
              ("Lama Saeed", "lama@example.com", "cv.pdf", make_pdf(CV_LINES[:9] + ["Skills", "SQL, Excel, Java", "Teamwork"])),
              ("Reem Omar", "reem@example.com", "scan.pdf", scanned_pdf())]
    apps = {}
    for name, email, fname, data in people:
        c.post("/api/auth/register", json={"email": email, "password": "Cand12345", "full_name": name}).raise_for_status()
        h = login(c, email, "Cand12345")
        r = c.post(f"/api/jobs/{jid}/applications", headers=h, files={"cv": (fname, io.BytesIO(data))})
        r.raise_for_status()
        apps[email] = (r.json()["id"], h)
    sara, sara_h = apps["sara@example.com"]
    lama, lama_h = apps["lama@example.com"]
    for app_id, ratings in [(sara, {"exp": 78, "edu": 85, "soft": 80}), (lama, {"exp": 70, "edu": 80, "soft": 75})]:
        c.put(f"/api/applications/{app_id}/ratings", headers=hr, json=ratings).raise_for_status()
    for app_id, h, answers, response in [(sara, sara_h, [1, 1], "Load the file with pandas, normalise emails, then drop_duplicates on email."),
                                         (lama, lama_h, [1, 0], None)]:
        tids = [t["id"] for t in c.post(f"/api/applications/{app_id}/assessments", headers=hr,
                                        json={"assessment_ids": [mcq, prac]}).json()]
        c.post(f"/api/attempts/{tids[0]}/start", headers=h)
        c.post(f"/api/attempts/{tids[0]}/submit", headers=h, json={"answers": answers})
        if response:
            c.post(f"/api/attempts/{tids[1]}/start", headers=h)
            c.post(f"/api/attempts/{tids[1]}/submit", headers=h, json={"response": response})
    for app_id in (sara, lama):
        c.post(f"/api/applications/{app_id}/evaluate", headers=hr).raise_for_status()
    c.post(f"/api/applications/{lama}/decision", headers=hr, json={"outcome": "reject", "reason": "Required Python evidence is missing"})
    c.post(f"/api/applications/{lama}/feedback", headers=hr).raise_for_status()
    return jid


def watch(page, label):
    page.on("console", lambda m: m.type == "error" and problems.append(f"{label}: console {m.text}"))
    page.on("pageerror", lambda e: problems.append(f"{label}: page error {e}"))
    page.on("response", lambda r: r.status >= 400 and "/api/" in r.url and problems.append(f"{label}: {r.status} {r.url}"))


def shot(page, name):
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(300)
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)


def ui_login(page, email, pw):
    page.goto(BASE + "/login.html")
    page.fill("#email", email)
    page.fill("#pw", pw)
    page.click("#submit")
    page.wait_for_load_state("networkidle")


def main():
    jid = seed()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 860})
        watch(page, "hr")
        page.goto(BASE + "/login.html")
        shot(page, "00_login")
        ui_login(page, "noura@hiremind.test", "HrPass1234")
        assert page.url.endswith("index.html"), page.url
        page.evaluate(f"localStorage.setItem('hm_job', '{jid}')")  # the job with applicants
        for name in ["index", "jobs", "candidates", "screening", "scoring", "verification", "feedback", "analytics", "learning", "settings"]:
            page.goto(f"{BASE}/{name}.html")
            shot(page, f"hr_{name}")
        # interactions: review a candidate, mark the practical answer, screening of the scanned CV
        page.goto(BASE + "/candidates.html"); page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Review", exact=True).first.click(); page.wait_for_timeout(500)
        shot(page, "hr_candidates_review")
        # ratings typed with Arabic-Indic digits, then evaluate and decide through the buttons
        for k, v in (("exp", "٨٠"), ("edu", "٨٥"), ("soft", "75")):
            page.fill(f"#r-{k}", v)
        page.get_by_role("button", name="Save ratings").click(); page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Evaluate now").click(); page.wait_for_load_state("networkidle")
        page.wait_for_timeout(300)
        assert "Not evaluated yet" not in page.inner_text("#ev"), "Evaluate now did not show a score"
        assert "Experience" in page.inner_text("#ev") and "80" in page.inner_text("#ev")
        shot(page, "hr_candidates_evaluated")
        page.select_option("#d-out", "advance")
        page.fill("#d-reason", "Strong SQL and Python evidence in the CV")
        page.get_by_role("button", name="Record decision").click(); page.wait_for_load_state("networkidle")
        page.wait_for_timeout(300)
        assert "advance" in page.inner_text("#list"), "decision not shown in the list"
        page.goto(BASE + "/verification.html"); page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Mark", exact=True).first.click(); page.wait_for_timeout(300)
        for i, v in enumerate(["5", "3"]):
            page.locator(".g-pt").nth(i).fill(v)
        page.get_by_role("button", name="Save marks").click(); page.wait_for_load_state("networkidle")
        shot(page, "hr_verification_after_marking")
        page.goto(BASE + "/screening.html"); page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Reem Omar").click(); page.wait_for_timeout(500)
        shot(page, "hr_screening_failed_cv")
        page.goto(BASE + "/feedback.html"); page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Approve this text").first.click(); page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Release to candidate").first.click(); page.wait_for_load_state("networkidle")
        shot(page, "hr_feedback_released")

        cand = browser.new_page(viewport={"width": 1366, "height": 860})
        watch(cand, "candidate")
        ui_login(cand, "lama@example.com", "Cand12345")
        assert cand.url.endswith("portal.html"), cand.url
        shot(cand, "cand_portal")
        cand.get_by_role("button", name="Read feedback").click(); cand.wait_for_timeout(300)
        shot(cand, "cand_feedback")
        cand.get_by_role("button", name="Close", exact=True).click()
        cand.get_by_role("button", name="Apply", exact=True).first.click()
        cand.set_input_files("#cv", files=[{"name": "lama_cv.docx", "mimeType": "application/octet-stream", "buffer": make_docx()}])
        cand.get_by_role("button", name="Submit application").click(); cand.wait_for_load_state("networkidle")
        shot(cand, "cand_after_apply")

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        watch(mobile, "mobile")
        ui_login(mobile, "noura@hiremind.test", "HrPass1234")
        shot(mobile, "mobile_dashboard")
        browser.close()
    if problems:
        print("\n".join(problems))
        sys.exit(f"{len(problems)} problem(s) found in the browser")
    print("E2E PASSED:", len(list(OUT.glob("*.png"))), "screenshots")


if __name__ == "__main__":
    main()
