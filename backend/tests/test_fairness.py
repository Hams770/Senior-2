"""FT-01 / NFR-09: ten CV pairs that differ only in an irrelevant attribute must get the same evidence and score."""
import pytest

from app.parser import parse_cv
from conftest import candidate, login, upload
from cvfiles import CV_LINES, make_docx

# (attribute, version A, version B) — the line that replaces the name/contact header
PAIRS = [
    ("name (female/male)", "Fatima Al-Qahtani", "Mohammed Al-Qahtani"),
    ("name (Arab/Western)", "Abdullah Hassan", "James Miller"),
    ("name (South Asian/East Asian)", "Priya Sharma", "Mei Chen"),
    ("nationality", "Nationality: Saudi", "Nationality: Egyptian"),
    ("nationality (non-Arab)", "Nationality: Filipino", "Nationality: British"),
    ("age", "Date of birth: 1999", "Date of birth: 1979"),
    ("marital status", "Marital status: single", "Marital status: married, two children"),
    ("religion", "Religion: Muslim", "Religion: Christian"),
    ("gender", "Gender: female", "Gender: male"),
    ("photo note", "Photo: attached", "Photo: not provided"),
]


def cv_with(header):
    return [header] + CV_LINES[1:]


@pytest.mark.parametrize("attribute,a,b", PAIRS)
def test_parser_ignores_irrelevant_attribute(attribute, a, b):
    pa, pb = parse_cv(make_docx(cv_with(a)), ".docx"), parse_cv(make_docx(cv_with(b)), ".docx")
    assert [s["skill"] for s in pa.skills] == [s["skill"] for s in pb.skills], attribute


def test_ft01_scores_identical_for_all_pairs(client):
    hr = login(client, "hr1@hm.test")
    jid = client.post("/api/jobs", headers=hr, json={"title": "Data Analyst", "description": "Reports with SQL and Python",
                                                    "required_skills": ["sql", "python", "power bi", "java"]}).json()["id"]
    client.post(f"/api/jobs/{jid}/publish", headers=hr)
    differences = []
    for i, (attribute, a, b) in enumerate(PAIRS):
        scores = []
        for side, header in (("a", a), ("b", b)):
            app_id = upload(client, candidate(client, f"p{i}{side}@hm.test"), jid, "cv.docx", make_docx(cv_with(header))).json()["id"]
            client.put(f"/api/applications/{app_id}/ratings", headers=hr, json={"exp": 70, "edu": 80, "soft": 75})
            scores.append(client.post(f"/api/applications/{app_id}/evaluate", headers=hr).json()["score"])
        if scores[0] != scores[1]:
            differences.append((attribute, scores))
    assert differences == [], differences
