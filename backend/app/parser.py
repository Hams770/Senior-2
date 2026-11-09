"""CV parser (FR-06 text, sections and skills; FR-07 source excerpt for every skill; FR-08 failures).

Only text-based PDF and DOCX files are supported; scanned CVs (images) are reported as failures,
because OCR is outside the pilot scope.
"""
import io
import re
from dataclasses import dataclass, field

from .skills import CONTEXT_ONLY, SECTION_HEADINGS, SKILLS

MIN_TEXT_CHARS = 200  # fewer characters than this usually means a scanned or empty CV
EXCERPT_CHARS = 160

_HEADING_LOOKUP = {h: name for name, hs in SECTION_HEADINGS.items() for h in hs}


class ParseError(Exception):
    """Raised with a message HR can understand (stored as the parse error)."""


@dataclass
class ParsedCV:
    text: str
    sections: dict[str, str]
    skills: list[dict] = field(default_factory=list)  # {"skill", "source_excerpt", "section"}


def extract_text(data: bytes, ext: str) -> str:
    try:
        if ext == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted:
                raise ParseError("The PDF is password-protected")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif ext == ".docx":
            import docx
            d = docx.Document(io.BytesIO(data))
            parts = [p.text for p in d.paragraphs]
            for table in d.tables:
                for row in table.rows:
                    parts.append(" | ".join(cell.text for cell in row.cells))
            text = "\n".join(parts)
        else:
            raise ParseError(f"Unsupported file type {ext}")
    except ParseError:
        raise
    except Exception as e:  # corrupted or unreadable file
        raise ParseError(f"The file could not be read ({type(e).__name__})") from e
    text = text.replace("\x00", "").replace("\r", "\n")
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    if len(text) < MIN_TEXT_CHARS:
        raise ParseError("Too little text was found; the CV may be a scanned image (not supported)")
    return text


def _heading(line: str) -> str | None:
    clean = re.sub(r"[^a-z &]", "", line.lower()).strip()
    if not clean or len(line.strip()) > 40:
        return None
    return _HEADING_LOOKUP.get(clean)


def split_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {"header": []}
    current = "header"
    for line in text.splitlines():
        name = _heading(line.rstrip(":").strip())
        if name:
            current = name
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


def _pattern(term: str) -> re.Pattern:
    # word boundaries that also work for terms such as c++, c#, .net and node.js
    # a space in a skill name also matches a line break, so "machine\nlearning" from a PDF still counts
    body = r"\s+".join(re.escape(part) for part in term.split())
    return re.compile(r"(?<![\w+#.])" + body + r"(?![\w+#])", re.IGNORECASE)


def _excerpt(text: str, start: int, end: int) -> str:
    """The sentence or line around a match, at most EXCERPT_CHARS long."""
    left = max(text.rfind("\n", 0, start), text.rfind(". ", 0, start)) + 1
    right_candidates = [i for i in (text.find("\n", end), text.find(". ", end)) if i != -1]
    right = min(right_candidates) if right_candidates else len(text)
    snippet = re.sub(r"\s+", " ", text[left:right]).strip()
    if len(snippet) > EXCERPT_CHARS:
        mid = start - left
        lo = max(0, mid - EXCERPT_CHARS // 2)
        snippet = ("…" if lo else "") + snippet[lo:lo + EXCERPT_CHARS].strip() + "…"
    return snippet


def extract_skills(sections: dict[str, str], extra_skills: list[str] = ()) -> list[dict]:
    vocab = {k: list(v) for k, v in SKILLS.items()}
    for s in extra_skills:  # the job's own required skills are always looked for
        key = s.strip().lower()
        if key:
            vocab.setdefault(key, []).append(key)
    order = ["skills"] + [k for k in sections if k != "skills"]  # prefer evidence from the skills section
    found: dict[str, dict] = {}
    for canonical, spellings in vocab.items():
        for sec in order:
            text = sections.get(sec)
            if not text:
                continue
            for spelling in sorted(set(spellings), key=len, reverse=True):
                if spelling in CONTEXT_ONLY and sec not in ("skills", "languages"):
                    continue
                m = _pattern(spelling).search(text)
                if m:
                    found[canonical] = {"skill": canonical, "section": sec,
                                        "source_excerpt": _excerpt(text, m.start(), m.end())}
                    break
            if canonical in found:
                break
    return sorted(found.values(), key=lambda s: s["skill"])


def parse_cv(data: bytes, ext: str, extra_skills: list[str] = ()) -> ParsedCV:
    text = extract_text(data, ext)
    sections = split_sections(text)
    return ParsedCV(text=text, sections=sections, skills=extract_skills(sections, extra_skills))
