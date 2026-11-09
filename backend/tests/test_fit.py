"""FR-09 / NFR-10: the fit prediction is stored, shown only to the owning HR, flagged for review by the
P(Good Fit) threshold, never changes the score, and its absence never blocks an application."""
import json

from app import config, fit_model
from conftest import candidate, login, published_job, upload
from cvfiles import make_pdf


def fake(p_good):
    """A stand-in model that gives P(Good Fit) = p_good and splits the rest between the other two labels."""
    seen = []

    def model(pairs):
        seen.extend(pairs)
        return [[(1 - p_good) * 0.6, (1 - p_good) * 0.4, p_good] for _ in pairs]
    model.seen = seen
    return model


def applied(client, p_good=0.5):
    model = fake(p_good)
    fit_model.set_backend(model)
    hr = login(client, "hr1@hm.test")
    jid = published_job(client, hr)
    r = upload(client, candidate(client), jid, "sara.pdf", make_pdf())
    assert r.status_code == 201, r.text
    return hr, jid, r.json()["id"], model


def test_fr09_prediction_is_stored_when_the_candidate_applies(client):
    hr, jid, app_id, model = applied(client, p_good=0.5)
    cv, job = model.seen[0]
    assert "Sara Ahmed" in cv and "Data Analyst" in job and "Required skills: sql, python" in job
    fit = client.get(f"/api/applications/{app_id}/fit", headers=hr).json()
    p = fit["prediction"]
    assert p["label"] == "Good Fit" and abs(sum(p["probabilities"].values()) - 1) < 1e-9
    assert p["model_version"].startswith("M0_s42_lr0.0001 (6ac7862e")
    row = client.get(f"/api/jobs/{jid}/candidates", headers=hr).json()[0]
    assert row["fit"]["label"] == "Good Fit"


def test_fr09_review_flag_follows_the_threshold(client):
    t = fit_model.CARD["review_threshold"]
    hr, _, app_id, _ = applied(client, p_good=t)  # at the threshold: flagged even though No Fit is the top label
    p = client.get(f"/api/applications/{app_id}/fit", headers=hr).json()["prediction"]
    assert p["needs_hr_review"] is True
    fit_model.set_backend(fake(t - 0.01))
    p = client.post(f"/api/applications/{app_id}/fit", headers=hr).json()["prediction"]
    assert p["needs_hr_review"] is False
    assert client.get("/api/analytics", headers=hr).json()["fit"]["predicted"] == 1


def test_fr09_prediction_never_changes_the_score(client):
    hr = login(client, "hr1@hm.test")
    jid = published_job(client, hr)
    scores, labels = [], []
    for i, p_good in enumerate((0.05, 0.95)):
        fit_model.set_backend(fake(p_good))
        app_id = upload(client, candidate(client, f"c{i}@hm.test"), jid, "sara.pdf", make_pdf()).json()["id"]
        assert client.put(f"/api/applications/{app_id}/ratings", headers=hr,
                          json={"exp": 70, "edu": 70, "soft": 70}).status_code == 200
        scores.append(client.post(f"/api/applications/{app_id}/evaluate", headers=hr).json()["score"])
        labels.append(client.get(f"/api/applications/{app_id}/fit", headers=hr).json()["prediction"]["label"])
    assert labels == ["No Fit", "Good Fit"] and scores[0] == scores[1]


def test_nfr10_application_works_without_the_classifier(client):
    hr = login(client, "hr1@hm.test")
    jid = published_job(client, hr)
    r = upload(client, candidate(client), jid, "sara.pdf", make_pdf())
    assert r.status_code == 201
    fit = client.get(f"/api/applications/{r.json()['id']}/fit", headers=hr).json()
    assert fit["prediction"] is None and fit["classifier"]["available"] is False and fit["classifier"]["reason"]
    assert client.post(f"/api/applications/{r.json()['id']}/fit", headers=hr).status_code == 503


def test_nfr10_a_failing_model_does_not_block_the_application(client):
    def broken(pairs):
        raise RuntimeError("out of memory")
    fit_model.set_backend(broken)
    hr = login(client, "hr1@hm.test")
    jid = published_job(client, hr)
    r = upload(client, candidate(client), jid, "sara.pdf", make_pdf())
    assert r.status_code == 201
    assert client.get(f"/api/applications/{r.json()['id']}/fit", headers=hr).json()["prediction"] is None


def test_fr09_weights_with_a_wrong_sha256_are_refused(tmp_path, monkeypatch):
    bad = tmp_path / "tampered.pt"
    bad.write_bytes(b"not the trained weights")
    monkeypatch.setattr(config, "FIT_ENABLED", True)
    monkeypatch.setattr(config, "FIT_WEIGHTS", bad)
    fit_model.reset()
    st = fit_model.status()
    assert st["available"] is False and "SHA-256 does not match" in st["reason"]


def test_fr09_shipped_weights_match_the_model_card():
    card = json.loads((config.MODEL_DIR / "fit_model.json").read_text())
    assert fit_model.sha256_file(config.MODEL_DIR / card["weights_file"]) == card["weights_sha256"]


def test_fr09_only_the_owning_hr_sees_the_prediction(client):
    _, _, app_id, _ = applied(client)
    other = login(client, "hr2@hm.test")
    assert client.get(f"/api/applications/{app_id}/fit", headers=other).status_code in (403, 404)
    cand = login(client, "cand@hm.test")
    assert client.get(f"/api/applications/{app_id}/fit", headers=cand).status_code == 403
    mine = client.get("/api/me/applications", headers=cand).json()[0]
    assert "fit" not in mine


def test_fr09_hr_correction_re_runs_the_model_on_the_corrected_text(client):
    hr, _, app_id, model = applied(client)
    r = client.patch(f"/api/applications/{app_id}/parsed", headers=hr,
                     json={"text": "Corrected CV text with SQL", "reason": "Fixed the extraction by hand"})
    assert r.status_code == 200, r.text
    assert model.seen[-1][0] == "Corrected CV text with SQL"
