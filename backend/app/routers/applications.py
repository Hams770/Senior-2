"""FR-05 CV upload (D4, D5 fixed), FR-06-08 parsing and HR correction, FR-19 status, NFR-04 private CV access."""
import hashlib
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select

from .. import audit, config
from ..models import Application, CVDocument, ExtractedSkill, Job
from ..parser import ParseError, parse_cv
from ..schemas import ApplicationOut, CorrectionIn, ParsedOut
from ..security import DB, CandidateUser, CurrentUser, HRUser
from .jobs import owned_job

router = APIRouter(prefix="/api", tags=["applications"])


async def read_valid_cv(file: UploadFile | None) -> tuple[bytes, str]:
    if file is None or not file.filename:
        raise HTTPException(422, "Select a CV file before submitting")  # D4
    ext = Path(file.filename).suffix.lower()
    if ext not in config.ALLOWED_CV_TYPES:
        raise HTTPException(415, "Only PDF and DOCX files are accepted")  # D5
    data = await file.read(config.MAX_CV_BYTES + 1)
    if not data:
        raise HTTPException(422, "The file is empty")  # D4
    if len(data) > config.MAX_CV_BYTES:
        raise HTTPException(413, "The CV must be 10 MB or smaller")
    if not data.startswith(config.ALLOWED_CV_TYPES[ext]):
        raise HTTPException(415, f"The file content is not a valid {ext[1:].upper()} file")
    return data, ext


@router.post("/jobs/{job_id}/applications", response_model=ApplicationOut, status_code=201)
async def apply(job_id: int, user: CandidateUser, db: DB, cv: Annotated[UploadFile | None, File()] = None):
    job = db.get(Job, job_id)
    if not job or job.status != "published":
        raise HTTPException(404, "This job is not open for applications")
    if db.scalar(select(Application).where(Application.job_id == job_id, Application.candidate_id == user.id)):
        raise HTTPException(409, "You have already applied to this job")
    data, ext = await read_valid_cv(cv)
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = config.UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"  # stored privately, never under its original name
    path.write_bytes(data)
    app = Application(job_id=job_id, candidate_id=user.id)
    db.add(app)
    db.flush()
    doc = CVDocument(application_id=app.id, original_name=Path(cv.filename).name, file_path=str(path),
                     sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data))
    db.add(doc)
    db.flush()
    run_parser(db, doc, data, ext, job.required_skills)
    audit.log(db, user.id, "apply", "application", app.id, job_id=job_id, parse_status=doc.parse_status)
    db.commit()
    return app


def run_parser(db, doc: CVDocument, data: bytes, ext: str, required_skills: list[str]) -> None:
    """FR-06/07; a failure is recorded with its reason instead of blocking the application (FR-08)."""
    for old in [s for s in doc.skills if s.origin == "parser"]:
        db.delete(old)
    try:
        parsed = parse_cv(data, ext, required_skills or [])
    except ParseError as e:
        doc.parse_status, doc.parse_error, doc.extracted_text, doc.sections = "failed", str(e), None, {}
        return
    doc.parse_status, doc.parse_error = "parsed", None
    doc.extracted_text, doc.sections = parsed.text, parsed.sections
    for s in parsed.skills:
        db.add(ExtractedSkill(cv_id=doc.id, skill=s["skill"], source_excerpt=s["source_excerpt"], section=s["section"]))


def hr_application(db, app_id: int, user) -> Application:
    app = db.get(Application, app_id)
    if not app or not app.cv:
        raise HTTPException(404, "Application not found")
    owned_job(db, app.job_id, user)
    return app


def parsed_view(db, app: Application) -> ParsedOut:
    db.refresh(app.cv)
    doc = app.cv
    return ParsedOut(application_id=app.id, parse_status=doc.parse_status, parse_error=doc.parse_error,
                     sections=doc.sections or {}, text=doc.corrected_text or doc.extracted_text,
                     original_text=doc.extracted_text, skills=doc.skills)


@router.get("/applications/{app_id}/parsed", response_model=ParsedOut)
def get_parsed(app_id: int, user: HRUser, db: DB):
    return parsed_view(db, hr_application(db, app_id, user))


@router.post("/applications/{app_id}/parse", response_model=ParsedOut)
def reparse(app_id: int, user: HRUser, db: DB):
    """Run the parser again on the stored file (for example after the parser is improved)."""
    app = hr_application(db, app_id, user)
    doc = app.cv
    if doc.parse_status == "corrected":
        raise HTTPException(409, "HR corrected this CV; re-parsing would hide the correction")
    data = Path(doc.file_path).read_bytes()
    run_parser(db, doc, data, Path(doc.file_path).suffix, db.get(Job, app.job_id).required_skills)
    audit.log(db, user.id, "reparse_cv", "application", app.id, parse_status=doc.parse_status)
    db.commit()
    return parsed_view(db, app)


@router.patch("/applications/{app_id}/parsed", response_model=ParsedOut)
def correct_parsed(app_id: int, body: CorrectionIn, user: HRUser, db: DB):
    """FR-08: HR corrects the text and/or skills; the parser's original output is kept."""
    app = hr_application(db, app_id, user)
    doc = app.cv
    if body.text is None and body.skills is None:
        raise HTTPException(422, "Send corrected text, skills, or both")
    if body.text is not None:
        doc.corrected_text = body.text
    if body.skills is not None:
        for s in doc.skills:
            if s.origin == "parser":
                s.active = False
            else:
                db.delete(s)
        for s in body.skills:
            db.add(ExtractedSkill(cv_id=doc.id, skill=s.skill.strip().lower(), source_excerpt=s.source_excerpt,
                                  section="hr", origin="hr"))
    doc.parse_status = "corrected"
    audit.log(db, user.id, "correct_cv", "application", app.id, reason=body.reason,
              text_changed=body.text is not None, skills=[s.skill for s in body.skills or []])
    db.commit()
    return parsed_view(db, app)


@router.get("/applications/mine", response_model=list[ApplicationOut])
def my_applications(user: CandidateUser, db: DB):
    return db.scalars(select(Application).where(Application.candidate_id == user.id)
                      .order_by(Application.id.desc())).all()


@router.get("/jobs/{job_id}/applications", response_model=list[ApplicationOut])
def job_applications(job_id: int, user: HRUser, db: DB):
    owned_job(db, job_id, user)
    return db.scalars(select(Application).where(Application.job_id == job_id)).all()


@router.get("/applications/{app_id}/cv")
def download_cv(app_id: int, user: CurrentUser, db: DB):
    app = db.get(Application, app_id)
    if not app or not app.cv:
        raise HTTPException(404, "Application not found")
    job = db.get(Job, app.job_id)
    allowed = (user.role == "admin" or (user.role == "candidate" and app.candidate_id == user.id)
               or (user.role == "hr" and job.owner_id == user.id))
    if not allowed:
        raise HTTPException(403, "You cannot access this CV")
    return FileResponse(app.cv.file_path, filename=app.cv.original_name)
