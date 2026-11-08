"""TC-03 job life cycle, TC-04 versioned scoring policy (D3), FR-22 audit."""
from conftest import candidate, login


def test_tc03_job_lifecycle(client):
    hr = login(client, "hr1@hm.test")
    cand = candidate(client)
    r = client.post("/api/jobs", headers=hr, json={"title": "ML Engineer", "description": "Build and deploy models",
                                                  "required_skills": ["python", "pytorch"]})
    jid = r.json()["id"]
    assert r.json()["status"] == "draft"
    assert client.get(f"/api/jobs/{jid}", headers=cand).status_code == 404       # drafts are hidden
    assert client.patch(f"/api/jobs/{jid}", headers=hr, json={"level": "senior"}).json()["level"] == "senior"
    assert client.post(f"/api/jobs/{jid}/publish", headers=hr).json()["status"] == "published"
    assert client.post(f"/api/jobs/{jid}/publish", headers=hr).status_code == 409
    assert [j["id"] for j in client.get("/api/jobs", headers=cand).json()] == [jid]
    assert client.post(f"/api/jobs/{jid}/close", headers=hr).json()["status"] == "closed"
    assert client.patch(f"/api/jobs/{jid}", headers=hr, json={"level": "x"}).status_code == 409
    assert client.get("/api/jobs", headers=cand).json() == []


def test_tc04_policy_versions_and_d3(client):
    hr = login(client, "hr1@hm.test")
    jid = client.post("/api/jobs", headers=hr, json={"title": "Analyst", "description": "Reports and dashboards"}).json()["id"]
    r = client.post(f"/api/jobs/{jid}/policies", headers=hr, json={"weights": {"tech": 50, "exp": 50}})
    assert r.status_code == 201 and r.json()["version"] == 2
    zero = {"tech": 0, "exp": 0, "edu": 0, "soft": 0, "ver": 0}
    assert client.post(f"/api/jobs/{jid}/policies", headers=hr, json={"weights": zero}).status_code == 422   # D3
    assert client.post(f"/api/jobs/{jid}/policies", headers=hr, json={"weights": {"tech": -5, "exp": 10}}).status_code == 422
    assert client.post(f"/api/jobs/{jid}/policies", headers=hr, json={"weights": {"salary": 10}}).status_code == 422
    versions = client.get(f"/api/jobs/{jid}/policies", headers=hr).json()
    assert [p["version"] for p in versions] == [1, 2]
    assert versions[0]["weights"]["tech"] == 35  # version 1 is the default and is kept


def test_fr22_audit_entries(client):
    hr = login(client, "hr1@hm.test")
    jid = client.post("/api/jobs", headers=hr, json={"title": "Analyst", "description": "Reports and dashboards"}).json()["id"]
    client.post(f"/api/jobs/{jid}/publish", headers=hr)
    log = client.get("/api/audit", headers=login(client, "admin@hm.test")).json()
    actions = [e["action"] for e in log if e["entity"] == "job" and e["entity_id"] == jid]
    assert {"create_job", "set_policy", "publish_job"} <= set(actions)
