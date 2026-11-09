"""Read endpoints shaped for the screens, and FR-21 analytics computed only from stored records."""
from collections import Counter

from fastapi import APIRouter
from sqlalchemy import select

from ..models import Application, AssessmentAttempt, Decision, Feedback, Job, User
from ..security import DB, CandidateUser, HRUser
from .assessments import attempt_view
from .evaluations import latest_evaluation
from .fit import fit_view, latest_fit
from .jobs import owned_job

router = APIRouter(prefix="/api", tags=["screens"])


def hr_jobs(db, user):
    q = select(Job)
    if user.role != "admin":
        q = q.where(Job.owner_id == user.id)
    return db.scalars(q).all()


@router.get("/jobs/{job_id}/candidates")
def job_candidates(job_id: int, user: HRUser, db: DB):
    owned_job(db, job_id, user)
    out = []
    for app in db.scalars(select(Application).where(Application.job_id == job_id).order_by(Application.id)):
        cand = db.get(User, app.candidate_id)
        ev = latest_evaluation(db, app.id)
        d = db.scalar(select(Decision).where(Decision.application_id == app.id))
        out.append({"application_id": app.id, "candidate": cand.full_name or cand.email.split("@")[0],
                    "email": cand.email, "status": app.status, "applied_at": app.created_at,
                    "parse_status": app.cv.parse_status if app.cv else None,
                    "skills": [s.skill for s in app.cv.skills if s.active] if app.cv else [],
                    "hr_ratings": app.hr_ratings, "score": ev.score if ev else None,
                    "stage": ev.stage if ev else None, "decision": d.outcome if d else None,
                    "final_outcome": app.final_outcome, "fit": fit_view(latest_fit(db, app.id))})
    return out


@router.get("/jobs/{job_id}/attempts")
def job_attempts(job_id: int, user: HRUser, db: DB, status: str | None = None):
    owned_job(db, job_id, user)
    q = (select(AssessmentAttempt).join(Application, Application.id == AssessmentAttempt.application_id)
         .where(Application.job_id == job_id))
    if status:
        q = q.where(AssessmentAttempt.status == status)
    views = []
    for t in db.scalars(q.order_by(AssessmentAttempt.id)):
        cand = db.get(User, db.get(Application, t.application_id).candidate_id)
        views.append({**attempt_view(t, True), "candidate": cand.full_name or cand.email})
    db.commit()
    return views


@router.get("/me/applications")
def my_applications_detail(user: CandidateUser, db: DB):
    out = []
    for app in db.scalars(select(Application).where(Application.candidate_id == user.id).order_by(Application.id.desc())):
        job = db.get(Job, app.job_id)
        n_released = len(db.scalars(select(Feedback).where(Feedback.application_id == app.id,
                                                           Feedback.status == "released")).all())
        n_todo = len(db.scalars(select(AssessmentAttempt).where(AssessmentAttempt.application_id == app.id,
                                                                AssessmentAttempt.status.in_(["assigned", "in_progress"]))).all())
        out.append({"application_id": app.id, "job_id": job.id, "job_title": job.title, "status": app.status,
                    "applied_at": app.created_at, "assessments_to_do": n_todo, "feedback_available": n_released > 0})
    return out


@router.get("/analytics")
def analytics(user: HRUser, db: DB):
    """FR-21: every number comes from the database; nothing is sample data."""
    jobs = hr_jobs(db, user)
    job_ids = [j.id for j in jobs]
    apps = db.scalars(select(Application).where(Application.job_id.in_(job_ids))).all() if job_ids else []
    app_ids = [a.id for a in apps]
    evs = [e for e in (latest_evaluation(db, a) for a in app_ids) if e]
    decisions = db.scalars(select(Decision).where(Decision.application_id.in_(app_ids))).all() if app_ids else []
    attempts = db.scalars(select(AssessmentAttempt).where(AssessmentAttempt.application_id.in_(app_ids))).all() if app_ids else []
    fits = [f for f in (latest_fit(db, a) for a in app_ids) if f]
    skill_counts = Counter(s.skill for a in apps if a.cv for s in a.cv.skills if s.active)
    per_job = []
    for j in jobs:
        js = [a for a in apps if a.job_id == j.id]
        scores = [e.score for e in evs if e.application_id in {a.id for a in js}]
        per_job.append({"job_id": j.id, "title": j.title, "status": j.status, "applications": len(js),
                        "evaluated": len(scores), "mean_score": sum(scores) / len(scores) if scores else None,
                        "policy_version": max((p.version for p in j.policies), default=None)})
    scores = [e.score for e in evs]
    return {
        "jobs": dict(Counter(j.status for j in jobs)),
        "applications": len(apps),
        "application_status": dict(Counter(a.status for a in apps)),
        "parse_status": dict(Counter(a.cv.parse_status for a in apps if a.cv)),
        "evaluations": {"evaluated": len(evs), "final": sum(e.stage == "final" for e in evs),
                        "mean_score": sum(scores) / len(scores) if scores else None,
                        "histogram": [sum(lo <= s < lo + 20 or (lo == 80 and s == 100) for s in scores) for lo in range(0, 100, 20)]},
        "decisions": dict(Counter(d.outcome for d in decisions)),
        "assessments": dict(Counter(t.status for t in attempts)),
        "fit": {"predicted": len(fits), "flagged_for_review": sum(f.needs_hr_review for f in fits),
                "labels": dict(Counter(fit_view(f)["label"] for f in fits))},
        "top_skills": skill_counts.most_common(10),
        "per_job": per_job,
    }
