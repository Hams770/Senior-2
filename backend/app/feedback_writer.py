"""Feedback drafts (FR-17). The writer only ever sees an anonymised summary: no name, email, phone or CV text.

With ANTHROPIC_API_KEY set, the draft comes from the LLM using the prompt in the midterm report (Appendix C);
otherwise, or if the call fails, a fixed template writes it. Either way HR edits and approves it (FR-18).
"""
import re

import httpx

from . import config

PROMPT = """You are helping an HR manager write feedback to a job applicant.
Write 120 to 180 words in a respectful, specific, and constructive tone.
Use only the information below. Do not guess any personal details,
and do not mention age, gender, nationality, religion, or appearance.

Job title: {job_title}
Required skills: {required_skills}
Decision: {decision}
Assessment results: {assessment_results}
Score components (0-100): {component_scores}

Explain the main strengths, the main gaps relative to the job,
and one or two concrete steps the applicant could take next.
The HR manager will review and edit this draft before it is sent."""

LABELS = {"tech": "required technical skills", "exp": "experience", "edu": "education",
          "soft": "soft skills", "ver": "skill assessments"}
DECISION_WORDS = {"advance": "moving forward to the next stage", "hold": "on hold for now",
                  "reject": "not moving forward"}
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def redact(text: str) -> str:
    return _PHONE.sub("[phone]", _EMAIL.sub("[email]", text))


def fill(summary: dict) -> str:
    return PROMPT.format(
        job_title=summary["job_title"],
        required_skills=", ".join(summary["required_skills"]) or "not specified",
        decision=summary["decision"],
        assessment_results="; ".join(f"{a['skill']} ({a['type']}): {a['result']}" for a in summary["assessments"])
        or "none assigned",
        component_scores=", ".join(f"{k} {v}" for k, v in summary["components"].items()))


def template_draft(summary: dict) -> str:
    comps = {k: v for k, v in summary["components"].items() if isinstance(v, (int, float))}
    strong = [LABELS[k] for k, v in sorted(comps.items(), key=lambda kv: -kv[1]) if v >= 70][:2]
    weak = [LABELS[k] for k, v in sorted(comps.items(), key=lambda kv: kv[1]) if v < 60][:2]
    missing = summary.get("missing_skills") or []
    lines = [f"Thank you for applying for the {summary['job_title']} position and for the time you gave to our process.",
             f"After reviewing your application, we are {DECISION_WORDS.get(summary['decision'], summary['decision'])}."]
    if strong:
        lines.append(f"Your application was strongest in {' and '.join(strong)}.")
    if weak or missing:
        gaps = weak + ([f"evidence of {', '.join(missing)}"] if missing else [])
        lines.append(f"The main gaps compared with this role were {' and '.join(gaps)}.")
    if missing:
        lines.append(f"A practical next step would be a short project or course that shows your use of {missing[0]}.")
    else:
        lines.append("A practical next step would be to add concrete examples and results to your CV for each skill.")
    lines.append("We wish you every success and encourage you to apply for future roles that match your profile.")
    return " ".join(lines)


MAX_RETRIES = 2  # NFR-06: a failed call is retried at most twice


def _call_llm(summary: dict) -> str:
    r = httpx.post("https://api.anthropic.com/v1/messages", timeout=config.LLM_TIMEOUT_S,
                   headers={"x-api-key": config.LLM_API_KEY, "anthropic-version": "2023-06-01",
                            "content-type": "application/json"},
                   json={"model": config.LLM_MODEL, "max_tokens": 600,
                         "messages": [{"role": "user", "content": fill(summary)}]})
    r.raise_for_status()
    return "".join(b.get("text", "") for b in r.json().get("content", [])).strip()


def write_draft(summary: dict) -> tuple[str, str, str]:
    """Returns (draft, source, model)."""
    if config.LLM_API_KEY:
        for attempt in range(1 + MAX_RETRIES):
            try:
                text = _call_llm(summary)
                if text:
                    return redact(text), "llm", config.LLM_MODEL
            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500 and e.response.status_code != 429:
                    break  # a request error (bad key, bad input) will not succeed on retry
            except (httpx.HTTPError, ValueError, KeyError):
                pass
    return template_draft(summary), "template", ""  # fall back instead of failing the request
