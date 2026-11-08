"""Non-functional tests against a running server (PT-01..03, RP-01, RT-01). Writes test-results/nfr_report.md.

    python nfr/run_nfr.py load      # seeds data and measures; server must be running on BASE
    python nfr/run_nfr.py persist   # after restarting the server: checks nothing was lost (RT-01)
"""
import io
import json
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "tests"))
from cvfiles import CV_LINES, make_docx, make_pdf  # noqa: E402

BASE = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8001"
OUT = ROOT / "test-results"
OUT.mkdir(exist_ok=True)
STATE = OUT / "nfr_state.json"


def p95(xs):
    return statistics.quantiles(xs, n=20)[18] if len(xs) >= 20 else max(xs)


def client():
    return httpx.Client(base_url=BASE, timeout=180)


def login(c, email, pw):
    r = c.post("/api/auth/login", data={"username": email, "password": pw})
    r.raise_for_status()
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def new_candidate(i, prefix):
    c = client()
    email = f"{prefix}{i}@load.test"
    c.post("/api/auth/register", json={"email": email, "password": "LoadTest123", "full_name": f"Candidate {i}"}).raise_for_status()
    return c, login(c, email, "LoadTest123")


def cv(i):
    # vary the skills so CVs are not identical
    extra = ["Java", "Docker", "Tableau", "Excel", "Spark"][i % 5]
    lines = CV_LINES[:-3] + ["Skills", f"Python, SQL, {extra}", "Projects", f"Project {i}: reporting pipeline with Power BI."]
    return ("cv.docx", make_docx(lines)) if i % 2 else ("cv.pdf", make_pdf(lines))


def load():
    c = client()
    admin = login(c, "admin@hiremind.test", "AdminPass123")
    c.post("/api/auth/staff", headers=admin, json={"email": "loadhr@load.test", "password": "LoadTest123", "role": "hr"})
    hr = login(c, "loadhr@load.test", "LoadTest123")
    jobs = []
    for title in ("Data Analyst", "Queue Test"):
        jid = c.post("/api/jobs", headers=hr, json={"title": title, "description": "Load test job with SQL and Python",
                                                    "required_skills": ["python", "sql", "power bi", "java"]}).json()["id"]
        c.post(f"/api/jobs/{jid}/publish", headers=hr).raise_for_status()
        jobs.append(jid)
    report = {}

    # PT-02: 50 CVs analysed (upload + parse), one after another
    times, statuses = [], []
    for i in range(50):
        cc, h = new_candidate(i, "pt2_")
        name, data = cv(i)
        t = time.perf_counter()
        r = cc.post(f"/api/jobs/{jobs[0]}/applications", headers=h, files={"cv": (name, io.BytesIO(data))})
        times.append(time.perf_counter() - t)
        statuses.append(r.status_code)
        app_id = r.json()["id"]
        c.put(f"/api/applications/{app_id}/ratings", headers=hr, json={"exp": 60 + i % 30, "edu": 70, "soft": 65})
        c.post(f"/api/applications/{app_id}/evaluate", headers=hr)
    parsed = sum(1 for x in c.get(f"/api/jobs/{jobs[0]}/candidates", headers=hr).json() if x["parse_status"] == "parsed")
    report["PT-02"] = {"cvs": 50, "p95_s": round(p95(times), 3), "max_s": round(max(times), 3), "target_s": 120,
                       "parsed": parsed, "pass": p95(times) <= 120 and all(s == 201 for s in statuses) and parsed == 50}

    # PT-01: 10 users x 20 dashboard requests
    paths = ["/api/analytics", "/api/jobs", f"/api/jobs/{jobs[0]}/candidates", f"/api/jobs/{jobs[0]}/ranking"]

    def user(u):
        cc, out = client(), []
        for k in range(20):
            t = time.perf_counter()
            r = cc.get(paths[(u + k) % len(paths)], headers=hr)
            out.append((time.perf_counter() - t, r.status_code))
        return out
    with ThreadPoolExecutor(10) as ex:
        results = [x for batch in ex.map(user, range(10)) for x in batch]
    lat = [t for t, _ in results]
    report["PT-01"] = {"requests": len(results), "users": 10, "p95_ms": round(1000 * p95(lat)), "max_ms": round(1000 * max(lat)),
                       "errors": sum(s != 200 for _, s in results), "target_ms": 2000,
                       "pass": p95(lat) <= 2 and all(s == 200 for _, s in results)}

    # PT-03: 100 applications submitted at the same time; none lost or duplicated
    def apply(i):
        cc, h = new_candidate(i, "pt3_")
        name, data = cv(i)
        return cc.post(f"/api/jobs/{jobs[1]}/applications", headers=h, files={"cv": (name, io.BytesIO(data))}).status_code
    with ThreadPoolExecutor(20) as ex:
        codes = list(ex.map(apply, range(100)))
    rows = c.get(f"/api/jobs/{jobs[1]}/candidates", headers=hr).json()
    ids = [r["application_id"] for r in rows]
    report["PT-03"] = {"submitted": 100, "accepted": codes.count(201), "stored": len(rows), "unique": len(set(ids)),
                       "parsed": sum(r["parse_status"] == "parsed" for r in rows),
                       "pass": codes.count(201) == 100 and len(rows) == 100 and len(set(ids)) == 100}

    # RP-01: identical inputs and policy give identical scores
    app_id = ids[0]
    c.put(f"/api/applications/{app_id}/ratings", headers=hr, json={"exp": 66, "edu": 77, "soft": 88})
    scores = [c.post(f"/api/applications/{app_id}/evaluate", headers=hr).json()["score"] for _ in range(5)]
    report["RP-01"] = {"evaluations": 5, "distinct_scores": len(set(scores)), "pass": len(set(scores)) == 1}

    STATE.write_text(json.dumps({"report": report, "jobs": jobs, "counts": {str(j): len(c.get(f"/api/jobs/{j}/candidates", headers=hr).json()) for j in jobs}}))
    print(json.dumps(report, indent=2))


def persist():
    state = json.loads(STATE.read_text())
    c = client()
    hr = login(c, "loadhr@load.test", "LoadTest123")
    now = {str(j): len(c.get(f"/api/jobs/{j}/candidates", headers=hr).json()) for j in state["jobs"]}
    report = state["report"]
    report["RT-01"] = {"before_restart": state["counts"], "after_restart": now, "pass": now == state["counts"]}
    rows = [("PT-01", "NFR-01", "Dashboard p95 ≤ 2 s, 10 users, 200 requests", f"p95 {report['PT-01']['p95_ms']} ms, {report['PT-01']['errors']} errors"),
            ("PT-02", "NFR-02", "CV analysis p95 ≤ 120 s over 50 CVs", f"p95 {report['PT-02']['p95_s']} s, {report['PT-02']['parsed']}/50 parsed"),
            ("PT-03", "NFR-03", "100 simultaneous applications, none lost or duplicated", f"{report['PT-03']['stored']} stored, {report['PT-03']['unique']} unique"),
            ("RP-01", "NFR-08", "Same inputs and policy give the same score", f"{report['RP-01']['distinct_scores']} distinct score in 5 runs"),
            ("RT-01", "NFR-06", "Data survives a server restart", f"{sum(now.values())} applications before and after")]
    md = ["# Non-functional test results", "", "Server: FastAPI on PostgreSQL 16, GitHub Actions runner (ubuntu-latest).", "",
          "| Test | Requirement | Target | Measured | Result |", "|---|---|---|---|---|"]
    md += [f"| {t} | {r} | {target} | {m} | {'Pass' if report[t]['pass'] else 'FAIL'} |" for t, r, target, m in rows]
    md += ["", "Security (ST-01), fairness (FT-01) and retry (RT-01) checks run in `backend/tests` (pytest).", "",
           "```json", json.dumps(report, indent=2), "```"]
    (OUT / "nfr_report.md").write_text("\n".join(md))
    print("\n".join(md))
    if not all(v["pass"] for v in report.values()):
        sys.exit("A non-functional target was not met")


if __name__ == "__main__":
    {"load": load, "persist": persist}[sys.argv[1]]()
