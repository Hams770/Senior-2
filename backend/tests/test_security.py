"""ST-01 / NFR-04: every protected endpoint refuses anonymous users, the wrong role and the wrong owner."""
import time

import jwt
import pytest

from app import config
from conftest import candidate, login, published_job, upload
from cvfiles import make_docx


@pytest.fixture()
def world(client):
    hr1, hr2 = login(client, "hr1@hm.test"), login(client, "hr2@hm.test")
    jid = published_job(client, hr1)
    cand, other = candidate(client, "c@hm.test"), candidate(client, "o@hm.test")
    app_id = upload(client, cand, jid, "cv.docx", make_docx()).json()["id"]
    aid = client.post(f"/api/jobs/{jid}/assessments", headers=hr1, json={"skill": "sql", "type": "practical",
        "prompt": "Explain a LEFT JOIN", "rubric": [{"criterion": "Correct", "max_points": 5}]}).json()["id"]
    tid = client.post(f"/api/applications/{app_id}/assessments", headers=hr1, json={"assessment_ids": [aid]}).json()[0]["id"]
    client.post(f"/api/applications/{app_id}/evaluate", headers=hr1)
    client.post(f"/api/applications/{app_id}/decision", headers=hr1, json={"outcome": "hold", "reason": "Need the assessment"})
    fid = client.post(f"/api/applications/{app_id}/feedback", headers=hr1).json()["id"]
    return dict(hr1=hr1, hr2=hr2, cand=cand, other=other, jid=jid, app=app_id, tid=tid, fid=fid)


HR_ONLY = [  # (method, path, body) — owner HR only
    ("PATCH", "/api/jobs/{jid}", {"title": "x"}), ("POST", "/api/jobs/{jid}/close", None),
    ("POST", "/api/jobs/{jid}/policies", {"weights": {"tech": 1}}), ("GET", "/api/jobs/{jid}/policies", None),
    ("GET", "/api/jobs/{jid}/applications", None), ("GET", "/api/jobs/{jid}/candidates", None),
    ("GET", "/api/jobs/{jid}/ranking", None), ("GET", "/api/jobs/{jid}/attempts", None),
    ("GET", "/api/jobs/{jid}/assessments", None),
    ("GET", "/api/applications/{app}/parsed", None), ("POST", "/api/applications/{app}/parse", None),
    ("PATCH", "/api/applications/{app}/parsed", {"skills": [], "reason": "test"}),
    ("PUT", "/api/applications/{app}/ratings", {"exp": 1}), ("POST", "/api/applications/{app}/evaluate", None),
    ("GET", "/api/applications/{app}/evaluations", None),
    ("POST", "/api/applications/{app}/decision", {"outcome": "reject", "reason": "not allowed here"}),
    ("POST", "/api/applications/{app}/outcome", {"outcome": "not_hired"}),
    ("POST", "/api/applications/{app}/assessments", {"assessment_ids": [1]}),
    ("POST", "/api/applications/{app}/feedback", None),
    ("POST", "/api/feedback/{fid}/approve", {}), ("POST", "/api/feedback/{fid}/release", None),
    ("POST", "/api/attempts/{tid}/grade", {"points": {"Correct": 1}}),
]


def call(client, method, path, body, headers, w):
    url = path.format(**w)
    return client.request(method, url, headers=headers, json=body) if body is not None else client.request(method, url, headers=headers)


@pytest.mark.parametrize("method,path,body", HR_ONLY)
def test_st01_hr_endpoints(client, world, method, path, body):
    w = world
    assert call(client, method, path, body, {}, w).status_code == 401              # anonymous
    assert call(client, method, path, body, w["cand"], w).status_code == 403       # wrong role
    assert call(client, method, path, body, w["hr2"], w).status_code == 403        # another company's HR


def test_st01_candidate_endpoints(client, world):
    w = world
    for path in ["/api/applications/{app}/assessments", "/api/applications/{app}/feedback", "/api/applications/{app}/cv"]:
        assert call(client, "GET", path, None, w["other"], w).status_code == 403
        assert call(client, "GET", path, None, w["hr2"], w).status_code == 403
    assert call(client, "POST", "/api/attempts/{tid}/start", None, w["other"], w).status_code == 404
    assert call(client, "POST", "/api/attempts/{tid}/start", None, w["hr1"], w).status_code == 403   # HR cannot take tests


def test_tokens_cannot_be_forged_or_reused_after_expiry(client, world):
    forged = jwt.encode({"sub": "1", "role": "admin", "exp": time.time() + 600}, "wrong-secret", algorithm="HS256")
    assert client.get("/api/audit", headers={"Authorization": f"Bearer {forged}"}).status_code == 401
    expired = jwt.encode({"sub": "1", "role": "admin", "exp": time.time() - 1}, config.SECRET_KEY, algorithm="HS256")
    assert client.get("/api/audit", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    none_alg = jwt.encode({"sub": "1", "role": "admin"}, None, algorithm="none")
    assert client.get("/api/audit", headers={"Authorization": f"Bearer {none_alg}"}).status_code == 401


def test_role_in_token_is_not_trusted(client, world):
    # a candidate who edits the role inside a validly signed token still gets candidate rights (role is read from the DB)
    me = client.get("/api/auth/me", headers=world["cand"]).json()
    tampered = jwt.encode({"sub": str(me["id"]), "role": "admin", "exp": time.time() + 600}, config.SECRET_KEY, algorithm="HS256")
    assert client.get("/api/audit", headers={"Authorization": f"Bearer {tampered}"}).status_code == 403


def test_uploads_cannot_choose_their_path_and_injection_is_inert(client, world):
    w = world
    r = upload(client, candidate(client, "p@hm.test"), w["jid"], "../../etc/passwd.docx", make_docx())
    assert r.status_code == 201
    with client.session_factory() as db:
        from app.models import CVDocument
        doc = db.query(CVDocument).filter_by(application_id=r.json()["id"]).one()
        assert ".." not in doc.file_path and doc.file_path.startswith(str(config.UPLOAD_DIR))
    evil = "x'); DROP TABLE users; --"
    client.patch(f"/api/jobs/{w['jid']}", headers=w["hr1"], json={"title": evil})
    assert client.get(f"/api/jobs/{w['jid']}", headers=w["hr1"]).json()["title"] == evil
    assert client.get("/api/auth/me", headers=w["hr1"]).status_code == 200      # users table still there


def test_passwords_are_hashed(client):
    with client.session_factory() as db:
        from app.models import User
        u = db.query(User).filter_by(email="hr1@hm.test").one()
        assert "Password123" not in u.password_hash and u.password_hash.startswith("pbkdf2_sha256$")
