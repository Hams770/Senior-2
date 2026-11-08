"""TC-01 authentication, TC-02 / ST-01 role and ownership checks."""
from conftest import candidate, login, published_job


def test_tc01_login_and_role(client):
    hr = login(client, "hr1@hm.test")
    me = client.get("/api/auth/me", headers=hr).json()
    assert me["role"] == "hr"
    assert client.post("/api/auth/login", data={"username": "hr1@hm.test", "password": "wrong"}).status_code == 401
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer forged"}).status_code == 401


def test_register_is_always_candidate_and_unique(client):
    r = client.post("/api/auth/register", json={"email": "x@hm.test", "password": "Password123", "role": "admin"})
    assert r.status_code == 201 and r.json()["role"] == "candidate"
    assert client.post("/api/auth/register", json={"email": "X@hm.test", "password": "Password123"}).status_code == 409
    assert client.post("/api/auth/register", json={"email": "bad", "password": "Password123"}).status_code == 422
    assert client.post("/api/auth/register", json={"email": "y@hm.test", "password": "short"}).status_code == 422


def test_tc02_roles_enforced_on_server(client):
    cand = candidate(client)
    hr = login(client, "hr1@hm.test")
    # candidate cannot create jobs, policies, staff or read the audit log
    assert client.post("/api/jobs", headers=cand, json={"title": "X", "description": "long enough text"}).status_code == 403
    assert client.post("/api/auth/staff", headers=cand, json={"email": "s@hm.test", "password": "Password123"}).status_code == 403
    assert client.get("/api/audit", headers=cand).status_code == 403
    # HR cannot create staff; admin can
    assert client.post("/api/auth/staff", headers=hr, json={"email": "s@hm.test", "password": "Password123"}).status_code == 403
    admin = login(client, "admin@hm.test")
    assert client.post("/api/auth/staff", headers=admin, json={"email": "s@hm.test", "password": "Password123"}).status_code == 201


def test_st01_ownership(client):
    hr1, hr2 = login(client, "hr1@hm.test"), login(client, "hr2@hm.test")
    jid = published_job(client, hr1)
    assert client.patch(f"/api/jobs/{jid}", headers=hr2, json={"title": "Hacked"}).status_code == 403
    assert client.post(f"/api/jobs/{jid}/close", headers=hr2).status_code == 403
    assert client.get(f"/api/jobs/{jid}/applications", headers=hr2).status_code == 403
    assert all(j["id"] != jid for j in client.get("/api/jobs", headers=hr2).json())
