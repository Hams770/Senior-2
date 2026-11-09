"""TC-06 extraction, TC-07 source excerpts, TC-08 failures and HR correction."""
import pytest

from app.parser import ParseError, parse_cv, split_sections
from conftest import candidate, login, published_job, upload
from cvfiles import make_docx, make_pdf, scanned_pdf

EXPECTED = {"python", "sql", "excel", "tableau", "git", "power bi", "postgresql", "pandas", "scikit-learn",
            "machine learning", "communication", "teamwork", "english", "arabic"}


@pytest.mark.parametrize("ext,data", [(".pdf", make_pdf()), (".docx", make_docx())])
def test_tc06_text_sections_and_skills(ext, data):
    p = parse_cv(data, ext)
    assert "Data analyst with two years" in p.text
    assert {"summary", "experience", "education", "skills", "projects"} <= set(p.sections)
    assert "Effat University" in p.sections["education"]
    assert {s["skill"] for s in p.skills} == EXPECTED


def test_tc07_every_skill_has_its_excerpt():
    p = parse_cv(make_pdf(), ".pdf")
    for s in p.skills:
        assert s["source_excerpt"] and len(s["source_excerpt"]) <= 162
    bi = next(s for s in p.skills if s["skill"] == "power bi")
    assert bi["section"] == "experience" and "dashboards" in bi["source_excerpt"]


def test_no_false_hits():
    # "Saudi Arabia" is not the skill Arabic; "go" and "r" in normal prose are not languages
    lines = ["Summary", "I go to work in Saudi Arabia and r eally like it. " * 8, "Skills", "Leadership"]
    found = {s["skill"] for s in parse_cv(make_pdf(lines), ".pdf").skills}
    assert found == {"leadership"}


def test_job_required_skills_are_matched():
    lines = ["Experience", "Prepared stakeholder reporting packs every month for the finance team. " * 4]
    found = {s["skill"] for s in parse_cv(make_pdf(lines), ".pdf", ["Stakeholder Reporting"]).skills}
    assert "stakeholder reporting" in found


def test_headings_are_recognised_flexibly():
    s = split_sections("Jane\nWORK EXPERIENCE:\nAnalyst\nTechnical Skills\nSQL")
    assert s["experience"] == "Analyst" and s["skills"] == "SQL"


def test_tc08_failures_have_reasons():
    with pytest.raises(ParseError, match="scanned"):
        parse_cv(scanned_pdf(), ".pdf")
    with pytest.raises(ParseError, match="could not be read"):
        parse_cv(b"%PDF-1.4 broken", ".pdf")
    with pytest.raises(ParseError, match="could not be read"):
        parse_cv(b"PK\x03\x04broken", ".docx")


def test_upload_parses_and_hr_sees_evidence(client):
    hr = login(client, "hr1@hm.test")
    jid = published_job(client, hr)
    app_id = upload(client, candidate(client), jid, "sara.docx", make_docx()).json()["id"]
    r = client.get(f"/api/applications/{app_id}/parsed", headers=hr).json()
    assert r["parse_status"] == "parsed" and {s["skill"] for s in r["skills"]} == EXPECTED
    assert client.get(f"/api/applications/{app_id}/parsed", headers=login(client, "hr2@hm.test")).status_code == 403


def test_tc08_failed_parse_is_recorded_then_hr_corrects(client):
    hr = login(client, "hr1@hm.test")
    jid = published_job(client, hr)
    app_id = upload(client, candidate(client), jid, "scan.pdf", scanned_pdf())
    assert app_id.status_code == 201                      # the application is not lost
    app_id = app_id.json()["id"]
    r = client.get(f"/api/applications/{app_id}/parsed", headers=hr).json()
    assert r["parse_status"] == "failed" and "scanned" in r["parse_error"]
    fix = {"text": "Typed by HR from the scanned CV", "reason": "Scanned CV",
           "skills": [{"skill": "SQL", "source_excerpt": "SQL reports (page 1)"}]}
    r = client.patch(f"/api/applications/{app_id}/parsed", headers=hr, json=fix).json()
    assert r["parse_status"] == "corrected" and r["text"].startswith("Typed by HR")
    assert [(s["skill"], s["origin"]) for s in r["skills"]] == [("sql", "hr")]
    assert client.post(f"/api/applications/{app_id}/parse", headers=hr).status_code == 409


def test_correction_keeps_parser_original(client):
    hr = login(client, "hr1@hm.test")
    jid = published_job(client, hr)
    app_id = upload(client, candidate(client), jid, "sara.pdf", make_pdf()).json()["id"]
    r = client.patch(f"/api/applications/{app_id}/parsed", headers=hr,
                     json={"skills": [{"skill": "python"}], "reason": "Remove weak matches"}).json()
    active = [s["skill"] for s in r["skills"] if s["active"]]
    kept = [s for s in r["skills"] if s["origin"] == "parser"]
    assert active == ["python"] and len(kept) == len(EXPECTED) and not any(s["active"] for s in kept)
    assert r["original_text"] == r["text"]                 # text not changed, original kept
    log = client.get("/api/audit", headers=login(client, "admin@hm.test")).json()
    assert any(e["action"] == "correct_cv" and e["detail"]["reason"] == "Remove weak matches" for e in log)


def test_skill_split_across_lines_and_languages_section():
    lines = ["Summary", "Built models with machine", "learning for churn prediction in retail stores. " * 3,
             "Languages", "Arabic (native), English (fluent)"]
    found = {s["skill"]: s for s in parse_cv(make_pdf(lines), ".pdf").skills}
    assert {"machine learning", "arabic", "english"} <= set(found)
    assert "\n" not in found["machine learning"]["source_excerpt"]
