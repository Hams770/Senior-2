"""TC-11 assign, TC-12 timed attempt, TC-13 key/rubric grading and NOT ASSESSED."""
from datetime import datetime, timedelta, timezone

import pytest

from app.routers import assessments as A
from conftest import candidate, login, published_job, upload

MCQ = {"skill": "sql", "type": "mcq", "time_limit_min": 10, "questions": [
    {"text": "Which clause filters groups?", "options": ["WHERE", "HAVING", "ORDER BY"], "answer": 1},
    {"text": "Which join keeps all left rows?", "options": ["INNER", "LEFT", "CROSS"], "answer": 1},
    {"text": "Which keyword removes duplicates?", "options": ["DISTINCT", "UNIQUE", "ONLY"], "answer": 0},
    {"text": "COUNT(*) counts?", "options": ["Rows", "Columns"], "answer": 0}]}
PRACTICAL = {"skill": "python", "type": "practical", "time_limit_min": 30,
             "prompt": "Explain how you would remove duplicate customers from a CSV file.",
             "rubric": [{"criterion": "Correct approach", "max_points": 6}, {"criterion": "Clarity", "max_points": 4}]}


@pytest.fixture()
def setup(client):
    hr = login(client, "hr1@hm.test")
    jid = published_job(client, hr)  # required skills: sql, python
    cand = candidate(client)
    app_id = upload(client, cand, jid).json()["id"]
    mcq = client.post(f"/api/jobs/{jid}/assessments", headers=hr, json=MCQ).json()
    prac = client.post(f"/api/jobs/{jid}/assessments", headers=hr, json=PRACTICAL).json()
    return client, hr, cand, jid, app_id, mcq, prac


def test_tc11_create_and_assign(setup):
    client, hr, cand, jid, app_id, mcq, prac = setup
    bad = {**MCQ, "skill": "java"}
    assert client.post(f"/api/jobs/{jid}/assessments", headers=hr, json=bad).status_code == 422   # not a required skill
    assert client.post(f"/api/jobs/{jid}/assessments", headers=hr, json={**MCQ, "questions": [
        {"text": "Bad key", "options": ["a", "b"], "answer": 5}]}).status_code == 422
    assert client.post(f"/api/jobs/{jid}/assessments", headers=cand, json=MCQ).status_code == 403
    r = client.post(f"/api/applications/{app_id}/assessments", headers=hr, json={"assessment_ids": [mcq["id"], prac["id"]]})
    assert r.status_code == 201 and len(r.json()) == 2
    again = client.post(f"/api/applications/{app_id}/assessments", headers=hr, json={"assessment_ids": [mcq["id"]]})
    assert again.json() == []                                                   # no duplicates
    assert client.get("/api/applications/mine", headers=cand).json()[0]["status"] == "assessment"
    hr2 = login(client, "hr2@hm.test")
    assert client.post(f"/api/applications/{app_id}/assessments", headers=hr2,
                       json={"assessment_ids": [mcq["id"]]}).status_code == 403


def test_candidate_never_sees_answer_key(setup):
    client, hr, cand, jid, app_id, mcq, prac = setup
    client.post(f"/api/applications/{app_id}/assessments", headers=hr, json={"assessment_ids": [mcq["id"]]})
    views = client.get(f"/api/applications/{app_id}/assessments", headers=cand).json()
    assert all("answer" not in q for q in views[0]["assessment"]["content"]["questions"])
    started = client.post(f"/api/attempts/{views[0]['id']}/start", headers=cand).json()
    assert all("answer" not in q for q in started["assessment"]["content"]["questions"])


def test_tc13_mcq_graded_by_key(setup):
    client, hr, cand, jid, app_id, mcq, prac = setup
    tid = client.post(f"/api/applications/{app_id}/assessments", headers=hr, json={"assessment_ids": [mcq["id"]]}).json()[0]["id"]
    assert client.post(f"/api/attempts/{tid}/submit", headers=cand, json={"answers": [1, 1, 0, 0]}).status_code == 409  # not started
    client.post(f"/api/attempts/{tid}/start", headers=cand)
    assert client.post(f"/api/attempts/{tid}/submit", headers=cand, json={"answers": [1]}).status_code == 422
    r = client.post(f"/api/attempts/{tid}/submit", headers=cand, json={"answers": [1, 0, 0, None]}).json()
    assert r["status"] == "graded" and r["score"] == 50.0                   # 2 of 4 correct
    assert client.post(f"/api/attempts/{tid}/submit", headers=cand, json={"answers": [1, 1, 0, 0]}).status_code == 409
    assert client.post(f"/api/attempts/{tid}/start", headers=cand).status_code == 409   # no restart


def test_tc12_time_limit_gives_not_assessed(setup, monkeypatch):
    client, hr, cand, jid, app_id, mcq, prac = setup
    tid = client.post(f"/api/applications/{app_id}/assessments", headers=hr, json={"assessment_ids": [mcq["id"]]}).json()[0]["id"]
    client.post(f"/api/attempts/{tid}/start", headers=cand)
    later = datetime.now(timezone.utc) + timedelta(minutes=11)
    monkeypatch.setattr(A, "now", lambda: later)
    r = client.post(f"/api/attempts/{tid}/submit", headers=cand, json={"answers": [1, 1, 0, 0]})
    assert r.status_code == 409 and "not assessed" in r.json()["detail"]
    view = client.get(f"/api/applications/{app_id}/assessments", headers=hr).json()[0]
    assert view["status"] == "expired" and view["score"] is None


def test_tc13_practical_rubric_by_hr(setup):
    client, hr, cand, jid, app_id, mcq, prac = setup
    tid = client.post(f"/api/applications/{app_id}/assessments", headers=hr, json={"assessment_ids": [prac["id"]]}).json()[0]["id"]
    client.post(f"/api/attempts/{tid}/start", headers=cand)
    assert client.post(f"/api/attempts/{tid}/submit", headers=cand, json={"response": "  "}).status_code == 422
    r = client.post(f"/api/attempts/{tid}/submit", headers=cand, json={"response": "Use pandas drop_duplicates on the email column."}).json()
    assert r["status"] == "submitted" and r["score"] is None
    assert client.post(f"/api/attempts/{tid}/grade", headers=cand, json={"points": {}}).status_code == 403
    assert client.post(f"/api/attempts/{tid}/grade", headers=hr, json={"points": {"Correct approach": 6}}).status_code == 422
    assert client.post(f"/api/attempts/{tid}/grade", headers=hr, json={"points": {"Correct approach": 9, "Clarity": 1}}).status_code == 422
    g = client.post(f"/api/attempts/{tid}/grade", headers=hr, json={"points": {"Correct approach": 5, "Clarity": 3}, "notes": "Good"}).json()
    assert g["status"] == "graded" and g["score"] == 80.0


def test_verification_component_is_not_assessed_until_all_graded(setup):
    client, hr, cand, jid, app_id, mcq, prac = setup
    ids = [t["id"] for t in client.post(f"/api/applications/{app_id}/assessments", headers=hr,
                                        json={"assessment_ids": [mcq["id"], prac["id"]]}).json()]
    with client.session_factory() as db:
        assert A.verification_score(db, app_id) is None
    client.post(f"/api/attempts/{ids[0]}/start", headers=cand)
    client.post(f"/api/attempts/{ids[0]}/submit", headers=cand, json={"answers": [1, 1, 0, 0]})   # 100
    with client.session_factory() as db:
        assert A.verification_score(db, app_id) is None                     # practical still missing (D1)
    client.post(f"/api/attempts/{ids[1]}/start", headers=cand)
    client.post(f"/api/attempts/{ids[1]}/submit", headers=cand, json={"response": "drop_duplicates"})
    client.post(f"/api/attempts/{ids[1]}/grade", headers=hr, json={"points": {"Correct approach": 3, "Clarity": 3}})
    with client.session_factory() as db:
        assert A.verification_score(db, app_id) == pytest.approx(80.0)     # (100 + 60) / 2


def test_other_candidate_cannot_touch_attempt(setup):
    client, hr, cand, jid, app_id, mcq, prac = setup
    tid = client.post(f"/api/applications/{app_id}/assessments", headers=hr, json={"assessment_ids": [mcq["id"]]}).json()[0]["id"]
    other = candidate(client, "other@hm.test")
    assert client.post(f"/api/attempts/{tid}/start", headers=other).status_code == 404
    assert client.get(f"/api/applications/{app_id}/assessments", headers=other).status_code == 403
