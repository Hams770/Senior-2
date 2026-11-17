"""Knowledge features for a CV-job pair, from the platform's own skill vocabulary (backend/app/skills.py).

These are facts the classifier would otherwise have to learn from 4,993 examples: which skills the job asks for,
which of them the CV shows, and the years of experience on each side. Used by the knowledge-signal check
(step 2) and, if the signal is real, as a short text line in front of the job description (step 3).
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.skills import CONTEXT_ONLY, SKILLS  # noqa: E402

_BOUND_L, _BOUND_R = r"(?<![\w+#.])", r"(?![\w+#])"
# plain dataset text has no sections, so the ambiguous spellings (go, swift, sales, ml, …) are not used
_PATTERNS = {canon: re.compile(_BOUND_L + "(?:" + "|".join(
    r"\s+".join(map(re.escape, s.split())) for s in sorted(set(sp), key=len, reverse=True) if s not in CONTEXT_ONLY)
    + ")" + _BOUND_R, re.IGNORECASE)
    for canon, sp in SKILLS.items() if any(s not in CONTEXT_ONLY for s in sp)}
_YEARS = re.compile(r"(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?(?:years?|yrs?)\b", re.IGNORECASE)


def skills_in(text: str) -> set[str]:
    return {c for c, p in _PATTERNS.items() if p.search(text)}


def years_in(text: str) -> int | None:
    ys = [int(m.group(1)) for m in _YEARS.finditer(text) if 0 < int(m.group(1)) <= 40]
    return max(ys) if ys else None


def features(cv: str, job: str) -> dict:
    js, cs = skills_in(job), skills_in(cv)
    found = js & cs
    jy, cy = years_in(job), years_in(cv)
    return {"job_skills": sorted(js), "found": sorted(found), "missing": sorted(js - cs),
            "n_job_skills": len(js), "n_found": len(found), "match_ratio": len(found) / len(js) if js else None,
            "job_years": jy, "cv_years": cy,
            "meets_years": None if jy is None or cy is None else int(cy >= jy)}


def knowledge_line(f: dict) -> str:
    """The text added in front of the job description (step 3)."""
    if not f["n_job_skills"]:
        return "Skills check: no listed skills recognised."
    parts = [f"Skills check: {f['n_found']} of {f['n_job_skills']} required skills found",
             "found: " + ", ".join(f["found"]) if f["found"] else "found: none"]
    if f["missing"]:
        parts.append("missing: " + ", ".join(f["missing"]))
    if f["meets_years"] is not None:
        parts.append(f"experience {f['cv_years']} years, job asks {f['job_years']}")
    return "; ".join(parts) + "."
