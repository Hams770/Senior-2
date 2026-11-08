"""Evaluation, ranking and HR decisions.

FR-10 provisional score from the evidence available; FR-14 final score only when every weighted component
has evidence; FR-15 ranking with shared ranks for ties and a breakdown of every score; FR-16 the HR decision
with its reason, never changed automatically; FR-20 the final hiring outcome.

Components (same five as the prototype):
  tech  share of the job's required skills found in the CV (parser or HR-corrected skills)
  exp, edu, soft  rated 0-100 by HR from the CV evidence
  ver   mean score of the assigned skill assessments
A component without evidence is NOT ASSESSED and is excluded (D1).
"""
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from .. import audit
from ..models import Application, Decision, Evaluation, Job, ScoringPolicy
from ..scoring import COMPONENTS, compute_score, rank
from ..security import DB, HRUser
from .assessments import verification_score
from .jobs import owned_job

router = APIRouter(prefix="/api", tags=["evaluation"])
HR_RATED = ("exp", "edu", "soft")


class RatingsIn(BaseModel):
    exp: float | None = Field(default=None, ge=0, le=100)
    edu: float | None = Field(default=None, ge=0, le=100)
    soft: float | None = Field(default=None, ge=0, le=100)
    note: str = ""


class DecisionIn(BaseModel):
    outcome: Literal["advance", "hold", "reject"]
    reason: str = Field(min_length=10)


class OutcomeIn(BaseModel):
    outcome: Literal["hired", "not_hired", "withdrawn"]
    note: str = ""


def hr_app(db, app_id: int, user) -> tuple[Application, Job]:
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(404, "Application not found")
    return app, owned_job(db, app.job_id, user)


def tech_component(app: Application, job: Job) -> tuple[float | None, list[str], list[str]]:
    required = sorted({s.strip().lower() for s in job.required_skills if s.strip()})
    if not required or not app.cv or app.cv.parse_status == "failed":
        return None, [], required  # no evidence yet (a failed parse needs HR correction first)
    found = {s.skill for s in app.cv.skills if s.active}
    matched = [s for s in required if s in found]
    return 100 * len(matched) / len(required), matched, [s for s in required if s not in found]


def components_for(db, app: Application, job: Job) -> tuple[dict, dict]:
    tech, matched, missing = tech_component(app, job)
    comps = {"tech": tech, "ver": verification_score(db, app.id)}
    comps.update({k: app.hr_ratings.get(k) for k in HR_RATED})
    return comps, {"matched_skills": matched, "missing_skills": missing}


def latest_policy(db, job_id: int) -> ScoringPolicy:
    return db.scalars(select(ScoringPolicy).where(ScoringPolicy.job_id == job_id)
                      .order_by(ScoringPolicy.version.desc())).first()


def latest_evaluation(db, app_id: int) -> Evaluation | None:
    return db.scalars(select(Evaluation).where(Evaluation.application_id == app_id)
                      .order_by(Evaluation.id.desc())).first()


def evaluation_view(ev: Evaluation, policy: ScoringPolicy) -> dict:
    return {"id": ev.id, "application_id": ev.application_id, "stage": ev.stage, "score": ev.score,
            "score_display": round(ev.score), "components": ev.components["values"],
            "not_assessed": ev.components["not_assessed"], "evidence": ev.components["evidence"],
            "policy_version": policy.version, "weights": policy.weights, "created_at": ev.created_at}


@router.put("/applications/{app_id}/ratings")
def set_ratings(app_id: int, body: RatingsIn, user: HRUser, db: DB):
    app, _ = hr_app(db, app_id, user)
    given = {k: v for k, v in body.model_dump(exclude={"note"}).items() if k in body.model_fields_set}
    if not given:
        raise HTTPException(422, "Rate at least one of exp, edu, soft (null clears a rating)")
    app.hr_ratings = {**app.hr_ratings, **given}
    app.hr_ratings = {k: v for k, v in app.hr_ratings.items() if v is not None}
    audit.log(db, user.id, "rate_application", "application", app.id, ratings=given, note=body.note)
    db.commit()
    return {"application_id": app.id, "hr_ratings": app.hr_ratings}


@router.post("/applications/{app_id}/evaluate", status_code=201)
def evaluate(app_id: int, user: HRUser, db: DB):
    app, job = hr_app(db, app_id, user)
    policy = latest_policy(db, job.id)
    comps, evidence = components_for(db, app, job)
    result = compute_score(comps, policy.weights)
    if result["score"] is None:
        raise HTTPException(409, "No evidence yet: parse the CV, rate the candidate or grade an assessment first")
    stage = "final" if result["complete"] else "provisional"  # FR-14
    ev = Evaluation(application_id=app.id, policy_id=policy.id, stage=stage, score=result["score"],
                    components={"values": {k: comps.get(k) for k in COMPONENTS},
                                "not_assessed": result["not_assessed"], "evidence": evidence})
    db.add(ev)
    db.flush()
    audit.log(db, user.id, "evaluate", "application", app.id, stage=stage, score=result["score"],
              policy_version=policy.version)
    db.commit()
    return evaluation_view(ev, policy)


@router.get("/applications/{app_id}/evaluations")
def evaluation_history(app_id: int, user: HRUser, db: DB):
    hr_app(db, app_id, user)
    evs = db.scalars(select(Evaluation).where(Evaluation.application_id == app_id).order_by(Evaluation.id)).all()
    return [evaluation_view(e, db.get(ScoringPolicy, e.policy_id)) for e in evs]


@router.get("/jobs/{job_id}/ranking")
def ranking(job_id: int, user: HRUser, db: DB, stage: Literal["any", "final"] = "any"):
    """FR-15: candidates ranked within one job by their latest evaluation; ties share a rank (D2)."""
    owned_job(db, job_id, user)
    rows = {}
    for app in db.scalars(select(Application).where(Application.job_id == job_id)):
        ev = latest_evaluation(db, app.id)
        if ev and (stage == "any" or ev.stage == "final"):
            decision = db.scalar(select(Decision).where(Decision.application_id == app.id))
            rows[app.id] = {**evaluation_view(ev, db.get(ScoringPolicy, ev.policy_id)),
                            "status": app.status, "decision": decision.outcome if decision else None}
    ranks = rank({k: v["score"] for k, v in rows.items()})
    out = [{"rank": ranks[k], **v} for k, v in rows.items()]
    return sorted(out, key=lambda r: (r["rank"], r["application_id"]))


@router.post("/applications/{app_id}/decision")
def decide(app_id: int, body: DecisionIn, user: HRUser, db: DB):
    """FR-16: only HR decides, always with a reason; nothing in the system changes it afterwards."""
    app, _ = hr_app(db, app_id, user)
    if app.final_outcome:
        raise HTTPException(409, "The hiring outcome is already recorded")
    ev = latest_evaluation(db, app.id)
    if ev is None:
        raise HTTPException(409, "Evaluate the application before deciding, so the decision is based on evidence")
    d = db.scalar(select(Decision).where(Decision.application_id == app.id))
    previous = d.outcome if d else None
    if d:
        d.outcome, d.reason, d.decided_by, d.evaluation_id = body.outcome, body.reason, user.id, ev.id
        d.updated_at = datetime.now(timezone.utc)
    else:
        d = Decision(application_id=app.id, decided_by=user.id, outcome=body.outcome, reason=body.reason,
                     evaluation_id=ev.id)
        db.add(d)
    app.status = "decided"
    db.flush()
    audit.log(db, user.id, "decide", "application", app.id, outcome=body.outcome, previous=previous,
              reason=body.reason, evaluation_id=ev.id, stage=ev.stage)
    db.commit()
    return {"application_id": app.id, "outcome": d.outcome, "reason": d.reason, "decided_by": d.decided_by,
            "evaluation_id": ev.id, "evaluation_stage": ev.stage, "previous": previous}


@router.post("/applications/{app_id}/outcome")
def record_outcome(app_id: int, body: OutcomeIn, user: HRUser, db: DB):
    """FR-20: the final hiring outcome, kept for future analysis (no automatic learning uses it)."""
    app, _ = hr_app(db, app_id, user)
    d = db.scalar(select(Decision).where(Decision.application_id == app.id))
    if body.outcome == "hired" and (not d or d.outcome != "advance"):
        raise HTTPException(409, "Only an application HR decided to advance can be marked hired")
    app.final_outcome = app.status = body.outcome
    audit.log(db, user.id, "record_outcome", "application", app.id, outcome=body.outcome, note=body.note)
    db.commit()
    return {"application_id": app.id, "status": app.status}
