"""FR-17 feedback drafts from an anonymised summary; FR-18 release only after HR approves (or edits) the text."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from .. import audit
from ..feedback_writer import write_draft
from ..models import Application, AssessmentAttempt, Decision, Feedback
from ..security import DB, CurrentUser, HRUser
from .evaluations import hr_app, latest_evaluation

router = APIRouter(prefix="/api", tags=["feedback"])


class ApproveIn(BaseModel):
    text: str | None = Field(default=None, min_length=20)  # the edited text; omitted = approve the draft as is


def view(f: Feedback, for_hr: bool) -> dict:
    if not for_hr:
        return {"id": f.id, "text": f.approved_text, "released_at": f.released_at}
    return {"id": f.id, "application_id": f.application_id, "status": f.status, "source": f.source,
            "model": f.model, "draft": f.draft, "approved_text": f.approved_text, "summary": f.summary,
            "created_at": f.created_at, "released_at": f.released_at}


def anonymised_summary(db, app: Application, job, decision: Decision) -> dict:
    ev = latest_evaluation(db, app.id)
    comps = ev.components["values"] if ev else {}
    attempts = db.scalars(select(AssessmentAttempt).where(AssessmentAttempt.application_id == app.id)).all()
    return {
        "job_title": job.title,
        "required_skills": job.required_skills,
        "decision": decision.outcome,
        "components": {k: (round(v) if v is not None else "not assessed") for k, v in comps.items()},
        "missing_skills": ev.components["evidence"].get("missing_skills", []) if ev else [],
        "assessments": [{"skill": t.assessment.skill, "type": t.assessment.type,
                         "result": f"{round(t.score)}/100" if t.score is not None else "not assessed"}
                        for t in attempts],
    }  # deliberately no name, email, CV text or decision reason


def hr_feedback(db, fid: int, user) -> Feedback:
    f = db.get(Feedback, fid)
    if not f:
        raise HTTPException(404, "Feedback not found")
    hr_app(db, f.application_id, user)
    return f


@router.post("/applications/{app_id}/feedback", status_code=201)
def create_draft(app_id: int, user: HRUser, db: DB):
    app, job = hr_app(db, app_id, user)
    decision = db.scalar(select(Decision).where(Decision.application_id == app.id))
    if not decision:
        raise HTTPException(409, "Record the HR decision before drafting feedback")
    for old in db.scalars(select(Feedback).where(Feedback.application_id == app.id, Feedback.status == "draft")):
        old.status = "discarded"
    summary = anonymised_summary(db, app, job, decision)
    text, source, model = write_draft(summary)
    f = Feedback(application_id=app.id, draft=text, source=source, model=model, summary=summary, created_by=user.id)
    db.add(f)
    db.flush()
    audit.log(db, user.id, "draft_feedback", "feedback", f.id, application_id=app.id, source=source)
    db.commit()
    return view(f, True)


@router.post("/feedback/{fid}/approve")
def approve(fid: int, body: ApproveIn, user: HRUser, db: DB):
    f = hr_feedback(db, fid, user)
    if f.status not in ("draft", "approved"):
        raise HTTPException(409, f"Feedback that is {f.status} cannot be approved")
    f.approved_text = body.text if body.text is not None else f.draft
    f.status, f.approved_by = "approved", user.id
    audit.log(db, user.id, "approve_feedback", "feedback", f.id, edited=body.text is not None)
    db.commit()
    return view(f, True)


@router.post("/feedback/{fid}/release")
def release(fid: int, user: HRUser, db: DB):
    f = hr_feedback(db, fid, user)
    if f.status != "approved":
        raise HTTPException(409, "Only feedback approved by HR can be released")  # FR-18
    f.status, f.released_at = "released", datetime.now(timezone.utc)
    audit.log(db, user.id, "release_feedback", "feedback", f.id)
    db.commit()
    return view(f, True)


@router.get("/applications/{app_id}/feedback")
def list_feedback(app_id: int, user: CurrentUser, db: DB):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404, "Application not found")
    if user.role == "candidate":
        if app.candidate_id != user.id:
            raise HTTPException(403, "Not your application")
        rows = db.scalars(select(Feedback).where(Feedback.application_id == app_id, Feedback.status == "released"))
        return [view(f, False) for f in rows]
    hr_app(db, app_id, user)
    return [view(f, True) for f in db.scalars(select(Feedback).where(Feedback.application_id == app_id)
                                               .order_by(Feedback.id))]
