"""RT-01 / NFR-06: failed LLM calls are retried at most twice, then the template is used; invalid files are rejected."""
import httpx

from app import config, feedback_writer

SUMMARY = {"job_title": "Analyst", "required_skills": ["sql"], "decision": "reject", "components": {"tech": 50},
           "missing_skills": ["sql"], "assessments": []}


def test_retries_at_most_twice_then_template(monkeypatch):
    calls = []

    def flaky(url, **kw):
        calls.append(1)
        raise httpx.ConnectError("down")
    monkeypatch.setattr(config, "LLM_API_KEY", "k")
    monkeypatch.setattr(feedback_writer.httpx, "post", flaky)
    text, source, _ = feedback_writer.write_draft(SUMMARY)
    assert len(calls) == 3 and source == "template" and "Analyst" in text


def test_recovers_on_second_try(monkeypatch):
    calls = []

    def second_ok(url, **kw):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(503, request=httpx.Request("POST", url))
        return httpx.Response(200, json={"content": [{"type": "text", "text": "Thank you for applying."}]},
                              request=httpx.Request("POST", url))
    monkeypatch.setattr(config, "LLM_API_KEY", "k")
    monkeypatch.setattr(feedback_writer.httpx, "post", second_ok)
    assert feedback_writer.write_draft(SUMMARY)[1] == "llm" and len(calls) == 2


def test_no_retry_on_bad_key(monkeypatch):
    calls = []

    def unauthorized(url, **kw):
        calls.append(1)
        return httpx.Response(401, request=httpx.Request("POST", url))
    monkeypatch.setattr(config, "LLM_API_KEY", "bad")
    monkeypatch.setattr(feedback_writer.httpx, "post", unauthorized)
    assert feedback_writer.write_draft(SUMMARY)[1] == "template" and len(calls) == 1
