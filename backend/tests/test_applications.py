"""TC-05 CV upload: D4 (no file) and D5 (only PDF/DOCX) fixed, 10 MB limit, private CV access (NFR-04)."""
from app import config
from conftest import DOCX, PDF, candidate, login, published_job, upload


def test_tc05_valid_pdf_and_docx(client):
    hr = login(client, "hr1@hm.test")
    jid = published_job(client, hr)
    r = upload(client, candidate(client, "a@hm.test"), jid, "Sara CV.pdf", PDF)
    assert r.status_code == 201 and r.json()["status"] == "submitted"
    assert upload(client, candidate(client, "b@hm.test"), jid, "cv.docx", DOCX).status_code == 201
    assert len(client.get(f"/api/jobs/{jid}/applications", headers=hr).json()) == 2


def test_d4_no_file_or_empty_file(client):
    jid = published_job(client, login(client, "hr1@hm.test"))
    cand = candidate(client)
    assert upload(client, cand, jid, None).status_code == 422
    assert upload(client, cand, jid, "cv.pdf", b"").status_code == 422


def test_d5_only_pdf_docx_with_matching_content(client):
    jid = published_job(client, login(client, "hr1@hm.test"))
    cand = candidate(client)
    assert upload(client, cand, jid, "cv.doc", b"\xd0\xcf\x11\xe0").status_code == 415
    assert upload(client, cand, jid, "cv.txt", b"hello").status_code == 415
    assert upload(client, cand, jid, "fake.pdf", b"MZ not a pdf").status_code == 415


def test_size_limit_and_duplicates_and_closed_job(client, monkeypatch):
    hr = login(client, "hr1@hm.test")
    jid = published_job(client, hr)
    cand = candidate(client)
    monkeypatch.setattr(config, "MAX_CV_BYTES", 100)
    assert upload(client, cand, jid, "big.pdf", PDF + b"0" * 200).status_code == 413
    monkeypatch.setattr(config, "MAX_CV_BYTES", 10 * 1024 * 1024)
    assert upload(client, cand, jid).status_code == 201
    assert upload(client, cand, jid).status_code == 409
    client.post(f"/api/jobs/{jid}/close", headers=hr)
    assert upload(client, candidate(client, "late@hm.test"), jid).status_code == 404


def test_cv_is_private(client):
    hr1, hr2 = login(client, "hr1@hm.test"), login(client, "hr2@hm.test")
    jid = published_job(client, hr1)
    owner, other = candidate(client, "o@hm.test"), candidate(client, "p@hm.test")
    app_id = upload(client, owner, jid).json()["id"]
    assert client.get(f"/api/applications/{app_id}/cv", headers=owner).content == PDF
    assert client.get(f"/api/applications/{app_id}/cv", headers=hr1).status_code == 200
    assert client.get(f"/api/applications/{app_id}/cv", headers=hr2).status_code == 403
    assert client.get(f"/api/applications/{app_id}/cv", headers=other).status_code == 403
    assert [a["id"] for a in client.get("/api/applications/mine", headers=owner).json()] == [app_id]   # FR-19
