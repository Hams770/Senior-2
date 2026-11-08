"""TC-10 provisional score, TC-14 final score, TC-15 ranking with ties, TC-16 HR decision, TC-20 outcome."""
import pytest

from conftest import candidate, login, upload
from cvfiles import make_docx

SQL_MCQ = {"skill": "sql", "type": "mcq", "time_limit_min": 10, "questions": [
    {"text": "Which clause filters groups?", "options": ["WHERE", "HAVING"], "answer": 1},
    {"text": "Which join keeps all left rows?", "options": ["INNER", "LEFT"], "answer": 1}]}


@pytest.fixture()
def job(client):
    hr = login(client, "hr1@hm.test")
    r = client.post("/api/jobs", headers=hr, json={"title": "Data Analyst", "description": "Reports with SQL and Python",
                                                  "required_skills": ["sql", "python", "tableau", "java"]})
    jid = r.json()["id"]
    client.post(f"/api/jobs/{jid}/publish", headers=hr)
    return hr, jid


def apply(client, jid, email):
    return upload(client, candidate(client, email), jid, "cv.docx", make_docx()).json()["id"]


def finish_assessment(client, hr, jid, app_id, email, answers):
    aid = client.post(f"/api/jobs/{jid}/assessments", headers=hr, json=SQL_MCQ).json()["id"]
    tid = client.post(f"/api/applications/{app_id}/assessments", headers=hr, json={"assessment_ids": [aid]}).json()[0]["id"]
    cand = login(client, email)
    client.post(f"/api/attempts/{tid}/start", headers=cand)
    client.post(f"/api/attempts/{tid}/submit", headers=cand, json={"answers": answers})


def test_tc10_provisional_from_available_evidence(client, job):
    hr, jid = job
    app_id = apply(client, jid, "sara@hm.test")
    r = client.post(f"/api/applications/{app_id}/evaluate", headers=hr).json()
    # the test CV has sql, python and tableau but not java -> tech = 75
    assert r["components"]["tech"] == 75.0 and r["evidence"]["missing_skills"] == ["java"]
    assert r["stage"] == "provisional" and sorted(r["not_assessed"]) == ["edu", "exp", "soft", "ver"]
    assert r["score"] == 75.0 and r["policy_version"] == 1


def test_tc14_final_only_with_all_evidence(client, job):
    hr, jid = job
    app_id = apply(client, jid, "sara@hm.test")
    client.put(f"/api/applications/{app_id}/ratings", headers=hr, json={"exp": 80, "edu": 90, "soft": 70})
    assert client.post(f"/api/applications/{app_id}/evaluate", headers=hr).json()["stage"] == "provisional"
    finish_assessment(client, hr, jid, app_id, "sara@hm.test", [1, 0])      # ver = 50
    r = client.post(f"/api/applications/{app_id}/evaluate", headers=hr).json()
    assert r["stage"] == "final" and r["not_assessed"] == []
    expected = (75 * 35 + 80 * 25 + 90 * 20 + 70 * 10 + 50 * 10) / 100
    assert r["score"] == pytest.approx(expected) and r["score_display"] == round(expected)
    assert len(client.get(f"/api/applications/{app_id}/evaluations", headers=hr).json()) == 2   # history kept


def test_policy_change_applies_to_next_evaluation(client, job):
    hr, jid = job
    app_id = apply(client, jid, "sara@hm.test")
    client.put(f"/api/applications/{app_id}/ratings", headers=hr, json={"exp": 50})
    client.post(f"/api/jobs/{jid}/policies", headers=hr, json={"weights": {"tech": 1, "exp": 1}})
    r = client.post(f"/api/applications/{app_id}/evaluate", headers=hr).json()
    assert r["policy_version"] == 2 and r["stage"] == "final" and r["score"] == pytest.approx(62.5)


def test_ratings_validation_and_clear(client, job):
    hr, jid = job
    app_id = apply(client, jid, "sara@hm.test")
    assert client.put(f"/api/applications/{app_id}/ratings", headers=hr, json={"exp": 120}).status_code == 422
    assert client.put(f"/api/applications/{app_id}/ratings", headers=hr, json={}).status_code == 422
    client.put(f"/api/applications/{app_id}/ratings", headers=hr, json={"exp": 60, "edu": 70})
    r = client.put(f"/api/applications/{app_id}/ratings", headers=hr, json={"exp": None}).json()
    assert r["hr_ratings"] == {"edu": 70}
    other = login(client, "hr2@hm.test")
    assert client.put(f"/api/applications/{app_id}/ratings", headers=other, json={"exp": 1}).status_code == 403


def test_tc15_ranking_ties_and_breakdown(client, job):
    hr, jid = job
    ids = [apply(client, jid, f"c{i}@hm.test") for i in range(3)]
    for app_id, exp in zip(ids, [80, 80, 40]):
        client.put(f"/api/applications/{app_id}/ratings", headers=hr, json={"exp": exp})
        client.post(f"/api/applications/{app_id}/evaluate", headers=hr)
    r = client.get(f"/api/jobs/{jid}/ranking", headers=hr).json()
    assert [x["rank"] for x in r] == [1, 1, 3]                               # D2: the two equal scores share rank 1
    assert r[0]["score"] == r[1]["score"] > r[2]["score"]
    assert {"components", "weights", "not_assessed", "evidence"} <= set(r[0])
    assert client.get(f"/api/jobs/{jid}/ranking?stage=final", headers=hr).json() == []
    assert client.get(f"/api/jobs/{jid}/ranking", headers=login(client, "hr2@hm.test")).status_code == 403


def test_tc16_hr_decision_with_reason_never_automatic(client, job):
    hr, jid = job
    app_id = apply(client, jid, "sara@hm.test")
    assert client.post(f"/api/applications/{app_id}/decision", headers=hr,
                       json={"outcome": "advance", "reason": "Strong SQL evidence"}).status_code == 409   # no evaluation yet
    client.post(f"/api/applications/{app_id}/evaluate", headers=hr)
    assert client.post(f"/api/applications/{app_id}/decision", headers=hr,
                       json={"outcome": "advance", "reason": "short"}).status_code == 422                # reason required
    cand = login(client, "sara@hm.test")
    assert client.post(f"/api/applications/{app_id}/decision", headers=cand,
                       json={"outcome": "advance", "reason": "I decide myself"}).status_code == 403
    d = client.post(f"/api/applications/{app_id}/decision", headers=hr,
                    json={"outcome": "hold", "reason": "Wait for the SQL assessment"}).json()
    assert d["outcome"] == "hold" and d["evaluation_stage"] == "provisional"
    # a new evaluation with a different score does NOT change the decision
    client.put(f"/api/applications/{app_id}/ratings", headers=hr, json={"exp": 10})
    client.post(f"/api/applications/{app_id}/evaluate", headers=hr)
    assert client.get(f"/api/jobs/{jid}/ranking", headers=hr).json()[0]["decision"] == "hold"
    d = client.post(f"/api/applications/{app_id}/decision", headers=hr,
                    json={"outcome": "advance", "reason": "Interview went well"}).json()
    assert d["previous"] == "hold" and d["outcome"] == "advance"
    assert client.get("/api/applications/mine", headers=cand).json()[0]["status"] == "decided"   # FR-19


def test_tc20_outcome(client, job):
    hr, jid = job
    a, b = apply(client, jid, "a@hm.test"), apply(client, jid, "b@hm.test")
    for app_id, outcome in [(a, "advance"), (b, "reject")]:
        client.post(f"/api/applications/{app_id}/evaluate", headers=hr)
        client.post(f"/api/applications/{app_id}/decision", headers=hr, json={"outcome": outcome, "reason": "Reviewed all evidence"})
    assert client.post(f"/api/applications/{b}/outcome", headers=hr, json={"outcome": "hired"}).status_code == 409
    assert client.post(f"/api/applications/{a}/outcome", headers=hr, json={"outcome": "hired"}).json()["status"] == "hired"
    assert client.post(f"/api/applications/{a}/decision", headers=hr,
                       json={"outcome": "reject", "reason": "Changed my mind later"}).status_code == 409
    log = client.get("/api/audit", headers=login(client, "admin@hm.test")).json()
    assert {"evaluate", "decide", "record_outcome"} <= {e["action"] for e in log}


def test_failed_parse_gives_no_tech_until_hr_corrects(client, job):
    from cvfiles import scanned_pdf
    hr, jid = job
    app_id = upload(client, candidate(client, "scan@hm.test"), jid, "scan.pdf", scanned_pdf()).json()["id"]
    assert client.post(f"/api/applications/{app_id}/evaluate", headers=hr).status_code == 409
    client.patch(f"/api/applications/{app_id}/parsed", headers=hr,
                 json={"skills": [{"skill": "sql"}, {"skill": "java"}], "reason": "Typed from scan"})
    assert client.post(f"/api/applications/{app_id}/evaluate", headers=hr).json()["components"]["tech"] == 50.0
