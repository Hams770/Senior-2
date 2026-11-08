"""FR-05 CV upload (D4, D5 fixed), FR-19 application status, NFR-04 private CV access."""
import hashlib
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select

from .. import audit, config
from ..models import Application, CVDocument, Job
from ..schemas import ApplicationOut
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
    db.add(CVDocument(application_id=app.id, original_name=Path(cv.filename).name, file_path=str(path),
                      sha256=hashlib.sha256(data).hexdigest(), size_bytes=len(data)))
    audit.log(db, user.id, "apply", "application", app.id, job_id=job_id)
    db.commit()
    return app


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
