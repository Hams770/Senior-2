"""TC-17 anonymised feedback drafts, TC-18 release only after HR approval."""
import json

import httpx
import pytest

from app import config, feedback_writer
from conftest import candidate, login, upload
from cvfiles import make_docx


@pytest.fixture()
def decided(client):
    hr = login(client, "hr1@hm.test")
    jid = client.post("/api/jobs", headers=hr, json={"title": "Data Analyst", "description": "Reports with SQL and Python",
                                                    "required_skills": ["sql", "python", "java"]}).json()["id"]
    client.post(f"/api/jobs/{jid}/publish", headers=hr)
    cand = candidate(client, "sara.ahmed@hm.test")
    app_id = upload(client, cand, jid, "cv.docx", make_docx()).json()["id"]
    client.put(f"/api/applications/{app_id}/ratings", headers=hr, json={"exp": 85, "edu": 90, "soft": 50})
    client.post(f"/api/applications/{app_id}/evaluate", headers=hr)
    return client, hr, cand, app_id


def test_draft_needs_decision(decided):
    client, hr, cand, app_id = decided
    assert client.post(f"/api/applications/{app_id}/feedback", headers=hr).status_code == 409


def test_tc17_template_draft_is_anonymised(decided):
    client, hr, cand, app_id = decided
    client.post(f"/api/applications/{app_id}/decision", headers=hr, json={"outcome": "reject", "reason": "Java is essential for this team"})
    f = client.post(f"/api/applications/{app_id}/feedback", headers=hr).json()
    assert f["source"] == "template" and f["status"] == "draft"
    assert "Data Analyst" in f["draft"] and "not moving forward" in f["draft"] and "java" in f["draft"]
    blob = json.dumps(f["summary"]) + f["draft"]
    for private in ["Sara", "sara.ahmed", "@", "Java is essential"]:          # no name, email or HR's private reason
        assert private not in blob
    assert f["summary"]["components"]["ver"] == "not assessed"


def test_tc18_release_only_after_approval(decided):
    client, hr, cand, app_id = decided
    client.post(f"/api/applications/{app_id}/decision", headers=hr, json={"outcome": "advance", "reason": "Strong evidence overall"})
    fid = client.post(f"/api/applications/{app_id}/feedback", headers=hr).json()["id"]
    assert client.post(f"/api/feedback/{fid}/release", headers=hr).status_code == 409
    assert client.get(f"/api/applications/{app_id}/feedback", headers=cand).json() == []    # nothing before release
    assert client.post(f"/api/feedback/{fid}/approve", headers=cand, json={}).status_code == 403
    edited = "Thank you for applying. We would like to invite you to an interview next week to discuss the role."
    a = client.post(f"/api/feedback/{fid}/approve", headers=hr, json={"text": edited}).json()
    assert a["status"] == "approved" and a["approved_text"] == edited and a["draft"] != edited   # draft kept
    client.post(f"/api/feedback/{fid}/release", headers=hr)
    seen = client.get(f"/api/applications/{app_id}/feedback", headers=cand).json()
    assert [s["text"] for s in seen] == [edited] and "draft" not in seen[0]
    assert client.post(f"/api/feedback/{fid}/approve", headers=hr, json={}).status_code == 409   # released is final
    other = candidate(client, "other@hm.test")
    assert client.get(f"/api/applications/{app_id}/feedback", headers=other).status_code == 403


def test_new_draft_discards_old_one(decided):
    client, hr, cand, app_id = decided
    client.post(f"/api/applications/{app_id}/decision", headers=hr, json={"outcome": "hold", "reason": "Waiting for assessment"})
    first = client.post(f"/api/applications/{app_id}/feedback", headers=hr).json()["id"]
    client.post(f"/api/applications/{app_id}/feedback", headers=hr)
    statuses = {f["id"]: f["status"] for f in client.get(f"/api/applications/{app_id}/feedback", headers=hr).json()}
    assert statuses[first] == "discarded" and list(statuses.values()).count("draft") == 1


def test_llm_used_when_key_set_and_redacted(decided, monkeypatch):
    client, hr, cand, app_id = decided
    client.post(f"/api/applications/{app_id}/decision", headers=hr, json={"outcome": "reject", "reason": "Missing Java experience"})
    sent = {}

    def fake_post(url, **kw):
        sent.update(kw["json"])
        return httpx.Response(200, json={"content": [{"type": "text", "text": "Dear applicant, call us on +966 55 123 4567."}]},
                              request=httpx.Request("POST", url))
    monkeypatch.setattr(config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(feedback_writer.httpx, "post", fake_post)
    f = client.post(f"/api/applications/{app_id}/feedback", headers=hr).json()
    assert f["source"] == "llm" and "[phone]" in f["draft"] and "4567" not in f["draft"]
    prompt = sent["messages"][0]["content"]
    assert "Job title: Data Analyst" in prompt and "sara" not in prompt.lower()


def test_llm_failure_falls_back_to_template(decided, monkeypatch):
    client, hr, cand, app_id = decided
    client.post(f"/api/applications/{app_id}/decision", headers=hr, json={"outcome": "reject", "reason": "Missing Java experience"})

    def broken(url, **kw):
        raise httpx.ConnectError("offline")
    monkeypatch.setattr(config, "LLM_API_KEY", "test-key")
    monkeypatch.setattr(feedback_writer.httpx, "post", broken)
    f = client.post(f"/api/applications/{app_id}/feedback", headers=hr)
    assert f.status_code == 201 and f.json()["source"] == "template"
