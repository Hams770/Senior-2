import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import config
from app.db import Base, get_db
from app.main import app
from app.models import User
from app.security import hash_password

PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
DOCX = b"PK\x03\x04" + b"\x00" * 100


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "uploads")
    with TestSession() as db:
        for email, role in [("admin@hm.test", "admin"), ("hr1@hm.test", "hr"), ("hr2@hm.test", "hr")]:
            db.add(User(email=email, role=role, full_name=role, password_hash=hash_password("Password123")))
        db.commit()
    c = TestClient(app)
    c.session_factory = TestSession
    yield c
    app.dependency_overrides.clear()


def login(client, email, password="Password123"):
    r = client.post("/api/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def candidate(client, email="cand@hm.test"):
    r = client.post("/api/auth/register", json={"email": email, "password": "Password123", "full_name": "Cand"})
    assert r.status_code == 201, r.text
    return login(client, email)


def published_job(client, hr):
    r = client.post("/api/jobs", headers=hr, json={"title": "Data Analyst", "description": "Analyse data with SQL and Python",
                                                  "required_skills": ["sql", "python"], "level": "junior"})
    assert r.status_code == 201, r.text
    jid = r.json()["id"]
    assert client.post(f"/api/jobs/{jid}/publish", headers=hr).status_code == 200
    return jid


def upload(client, headers, job_id, name="cv.pdf", data=PDF):
    files = {"cv": (name, io.BytesIO(data), "application/octet-stream")} if name is not None else None
    return client.post(f"/api/jobs/{job_id}/applications", headers=headers, files=files)
