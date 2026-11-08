"""PS-01..06 from the midterm, plus fixes D1-D3 and NFR-08 repeatability."""
import pytest

from app.scoring import DEFAULT_WEIGHTS, PolicyError, compute_score, rank

SARA = {"tech": 93, "exp": 90, "edu": 92, "soft": 91, "ver": 95}


def test_prototype_formula_unchanged():
    # same weighted mean as computeScore() in scoring.html: Sara scores 92
    assert round(compute_score(SARA, DEFAULT_WEIGHTS)["score"]) == 92


def test_d1_not_assessed_is_excluded_not_zero():
    omar = {"tech": 84, "exp": 76, "edu": 82, "soft": 79, "ver": None}
    r = compute_score(omar, DEFAULT_WEIGHTS)
    assert r["not_assessed"] == ["ver"] and r["complete"] is False
    expected = (84 * 35 + 76 * 25 + 82 * 20 + 79 * 10) / 90
    assert r["score"] == pytest.approx(expected)          # about 80.9, not 73 as with ver = 0
    assert compute_score({**omar, "ver": 0}, DEFAULT_WEIGHTS)["score"] < r["score"]


def test_fr14_complete_only_with_all_evidence():
    assert compute_score(SARA, DEFAULT_WEIGHTS)["complete"] is True
    # a component with zero weight is not required
    assert compute_score({**SARA, "ver": None}, {**DEFAULT_WEIGHTS, "ver": 0})["complete"] is True


def test_d2_ties_share_rank():
    assert rank({1: 87.0, 2: 92.0, 3: 87.0, 4: 71.0}) == {2: 1, 1: 2, 3: 2, 4: 4}


def test_d3_zero_or_invalid_weights_rejected():
    with pytest.raises(PolicyError):
        compute_score(SARA, {k: 0 for k in DEFAULT_WEIGHTS})
    with pytest.raises(PolicyError):
        compute_score(SARA, {"tech": -1, "exp": 5})
    with pytest.raises(ValueError):
        compute_score({**SARA, "tech": 130}, DEFAULT_WEIGHTS)


def test_nfr08_repeatable():
    assert all(compute_score(SARA, DEFAULT_WEIGHTS) == compute_score(SARA, DEFAULT_WEIGHTS) for _ in range(5))


def test_preview_endpoint(client):
    from conftest import login
    hr = login(client, "hr1@hm.test")
    r = client.post("/api/scoring/preview", headers=hr, json={"components": SARA, "weights": DEFAULT_WEIGHTS})
    assert r.status_code == 200 and round(r.json()["score"]) == 92
    bad = client.post("/api/scoring/preview", headers=hr, json={"components": SARA, "weights": {"tech": 0}})
    assert bad.status_code == 422
