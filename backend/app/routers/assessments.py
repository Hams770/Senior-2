"""Skill verification (FR-11 assign, FR-12 timed attempt, FR-13 key/rubric grading, NOT ASSESSED when missing).

MCQ answers are graded automatically from the answer key, which candidates never see.
Practical answers are text only (candidate code is never executed) and HR grades them with a rubric.
"""
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select

from .. import audit
from ..models import Application, Assessment, AssessmentAttempt
from ..security import DB, CandidateUser, CurrentUser, HRUser
from .jobs import owned_job

router = APIRouter(prefix="/api", tags=["assessments"])
GRACE = timedelta(seconds=30)  # network delay allowance after the time limit


def now() -> datetime:
    return datetime.now(timezone.utc)


def aware(dt: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; all stored times are UTC."""
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


# ---------- request bodies ----------
class MCQQuestion(BaseModel):
    text: str = Field(min_length=3)
    options: list[str] = Field(min_length=2, max_length=6)
    answer: int  # index of the correct option

    @model_validator(mode="after")
    def check_answer(self):
        if not 0 <= self.answer < len(self.options):
            raise ValueError("answer must be the index of one of the options")
        return self


class Criterion(BaseModel):
    criterion: str = Field(min_length=2)
    max_points: float = Field(gt=0)


class AssessmentIn(BaseModel):
    skill: str = Field(min_length=1)
    type: Literal["mcq", "practical"]
    title: str = ""
    time_limit_min: int = Field(default=30, ge=1, le=240)
    questions: list[MCQQuestion] | None = None
    prompt: str | None = None
    rubric: list[Criterion] | None = None

    @model_validator(mode="after")
    def check_content(self):
        if self.type == "mcq" and not self.questions:
            raise ValueError("An MCQ assessment needs at least one question")
        if self.type == "practical" and (not self.prompt or not self.rubric):
            raise ValueError("A practical assessment needs a prompt and a rubric")
        return self


class AssignIn(BaseModel):
    assessment_ids: list[int] = Field(min_length=1)


class SubmitIn(BaseModel):
    answers: list[int | None] | None = None  # mcq: chosen option per question
    response: str | None = None  # practical: written answer


class GradeIn(BaseModel):
    points: dict[str, float]
    notes: str = ""


# ---------- views ----------
def assessment_view(a: Assessment, with_key: bool) -> dict:
    content = a.content
    if a.type == "mcq" and not with_key:
        content = {"questions": [{"text": q["text"], "options": q["options"]} for q in content["questions"]]}
    return {"id": a.id, "job_id": a.job_id, "skill": a.skill, "type": a.type, "title": a.title,
            "time_limit_min": a.time_limit_min, "content": content}


def attempt_view(t: AssessmentAttempt, for_hr: bool) -> dict:
    expire_if_late(t)
    view = {"id": t.id, "application_id": t.application_id, "status": t.status, "score": t.score,
            "assessment": assessment_view(t.assessment, with_key=for_hr),
            "started_at": aware(t.started_at), "expires_at": aware(t.expires_at),
            "submitted_at": aware(t.submitted_at)}
    if for_hr or t.status in ("submitted", "graded"):
        view["answers"] = t.answers
    if for_hr or t.status == "graded":
        view.update(points=t.points, grader_notes=t.grader_notes)
    return view


def expire_if_late(t: AssessmentAttempt) -> None:
    """FR-12/13: an attempt that ran out of time without a submission is NOT ASSESSED."""
    if t.status == "in_progress" and now() > aware(t.expires_at) + GRACE:
        t.status, t.score = "expired", None


# ---------- HR: create and assign (FR-11) ----------
@router.post("/jobs/{job_id}/assessments", status_code=201)
def create_assessment(job_id: int, body: AssessmentIn, user: HRUser, db: DB):
    job = owned_job(db, job_id, user)
    skill = body.skill.strip().lower()
    if skill not in [s.strip().lower() for s in job.required_skills]:
        raise HTTPException(422, f"'{skill}' is not one of this job's required skills")
    content = ({"questions": [q.model_dump() for q in body.questions]} if body.type == "mcq"
               else {"prompt": body.prompt, "rubric": [c.model_dump() for c in body.rubric]})
    a = Assessment(job_id=job.id, skill=skill, type=body.type, title=body.title or f"{skill} {body.type}",
                   content=content, time_limit_min=body.time_limit_min, created_by=user.id)
    db.add(a)
    db.flush()
    audit.log(db, user.id, "create_assessment", "assessment", a.id, job_id=job.id, skill=skill, type=body.type)
    db.commit()
    return assessment_view(a, with_key=True)


@router.get("/jobs/{job_id}/assessments")
def list_assessments(job_id: int, user: HRUser, db: DB):
    owned_job(db, job_id, user)
    return [assessment_view(a, True) for a in db.scalars(select(Assessment).where(Assessment.job_id == job_id))]


@router.post("/applications/{app_id}/assessments", status_code=201)
def assign(app_id: int, body: AssignIn, user: HRUser, db: DB):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404, "Application not found")
    owned_job(db, app.job_id, user)
    created = []
    for aid in dict.fromkeys(body.assessment_ids):
        a = db.get(Assessment, aid)
        if not a or a.job_id != app.job_id:
            raise HTTPException(422, f"Assessment {aid} does not belong to this job")
        if db.scalar(select(AssessmentAttempt).where(AssessmentAttempt.assessment_id == aid,
                                                     AssessmentAttempt.application_id == app_id)):
            continue
        t = AssessmentAttempt(assessment_id=aid, application_id=app_id)
        db.add(t)
        created.append(t)
    if created and app.status == "submitted":
        app.status = "assessment"
    db.flush()
    audit.log(db, user.id, "assign_assessments", "application", app_id, assessment_ids=body.assessment_ids)
    db.commit()
    return [attempt_view(t, True) for t in created]


# ---------- both: list attempts of an application ----------
@router.get("/applications/{app_id}/assessments")
def application_attempts(app_id: int, user: CurrentUser, db: DB):
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404, "Application not found")
    if user.role == "candidate":
        if app.candidate_id != user.id:
            raise HTTPException(403, "Not your application")
    else:
        owned_job(db, app.job_id, user)
    attempts = db.scalars(select(AssessmentAttempt).where(AssessmentAttempt.application_id == app_id)).all()
    views = [attempt_view(t, user.role != "candidate") for t in attempts]
    db.commit()  # persists any expiry detected while viewing
    return views


# ---------- candidate: timed attempt (FR-12) ----------
def own_attempt(db, attempt_id: int, user) -> AssessmentAttempt:
    t = db.get(AssessmentAttempt, attempt_id)
    if not t or db.get(Application, t.application_id).candidate_id != user.id:
        raise HTTPException(404, "Assessment not found")
    return t


@router.post("/attempts/{attempt_id}/start")
def start(attempt_id: int, user: CandidateUser, db: DB):
    t = own_attempt(db, attempt_id, user)
    if t.status != "assigned":
        raise HTTPException(409, f"This assessment cannot be started (status: {t.status})")
    t.status, t.started_at = "in_progress", now()
    t.expires_at = t.started_at + timedelta(minutes=t.assessment.time_limit_min)
    db.commit()
    return attempt_view(t, for_hr=False)


@router.post("/attempts/{attempt_id}/submit")
def submit(attempt_id: int, body: SubmitIn, user: CandidateUser, db: DB):
    t = own_attempt(db, attempt_id, user)
    expire_if_late(t)
    if t.status == "expired":
        db.commit()
        raise HTTPException(409, "The time limit has passed; this assessment is recorded as not assessed")
    if t.status != "in_progress":
        raise HTTPException(409, f"This assessment is not in progress (status: {t.status})")
    a = t.assessment
    if a.type == "mcq":
        questions = a.content["questions"]
        if body.answers is None or len(body.answers) != len(questions):
            raise HTTPException(422, f"Send one answer per question ({len(questions)})")
        correct = sum(1 for q, ans in zip(questions, body.answers) if ans == q["answer"])
        t.answers = {"choices": body.answers, "correct": correct, "total": len(questions)}
        t.score, t.status = 100 * correct / len(questions), "graded"  # FR-13 graded by key
    else:
        if not body.response or not body.response.strip():
            raise HTTPException(422, "Write your answer before submitting")
        t.answers, t.status = {"response": body.response}, "submitted"
    t.submitted_at = now()
    audit.log(db, user.id, "submit_assessment", "assessment_attempt", t.id, status=t.status)
    db.commit()
    return attempt_view(t, for_hr=False)


# ---------- HR: rubric grading (FR-13) ----------
@router.post("/attempts/{attempt_id}/grade")
def grade(attempt_id: int, body: GradeIn, user: HRUser, db: DB):
    t = db.get(AssessmentAttempt, attempt_id)
    if not t:
        raise HTTPException(404, "Attempt not found")
    owned_job(db, db.get(Application, t.application_id).job_id, user)
    if t.assessment.type != "practical" or t.status != "submitted":
        raise HTTPException(409, "Only a submitted practical answer is graded by rubric")
    rubric = {c["criterion"]: c["max_points"] for c in t.assessment.content["rubric"]}
    if set(body.points) != set(rubric):
        raise HTTPException(422, f"Give points for exactly these criteria: {sorted(rubric)}")
    for k, v in body.points.items():
        if not 0 <= v <= rubric[k]:
            raise HTTPException(422, f"Points for '{k}' must be between 0 and {rubric[k]}")
    t.points, t.grader_notes, t.graded_by = body.points, body.notes, user.id
    t.score, t.status = 100 * sum(body.points.values()) / sum(rubric.values()), "graded"
    audit.log(db, user.id, "grade_assessment", "assessment_attempt", t.id, score=t.score)
    db.commit()
    return attempt_view(t, for_hr=True)


def verification_score(db, app_id: int) -> float | None:
    """The 'ver' scoring component: mean of graded attempts; None (NOT ASSESSED) if any is not graded."""
    attempts = db.scalars(select(AssessmentAttempt).where(AssessmentAttempt.application_id == app_id)).all()
    for t in attempts:
        expire_if_late(t)
    if not attempts or any(t.score is None for t in attempts):
        return None
    return sum(t.score for t in attempts) / len(attempts)
