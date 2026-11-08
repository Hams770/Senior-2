"""FR-03 jobs and FR-04 versioned scoring policies."""
from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from .. import audit
from ..models import Job, ScoringPolicy, User
from ..schemas import JobIn, JobOut, JobUpdate, PolicyIn, PolicyOut
from ..scoring import DEFAULT_WEIGHTS, PolicyError, validate_weights
from ..security import DB, CurrentUser, HRUser

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def owned_job(db, job_id: int, user: User) -> Job:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if user.role != "admin" and job.owner_id != user.id:
        raise HTTPException(403, "You do not own this job")  # FR-02 ownership
    return job


def add_policy(db, job: Job, weights: dict, user: User) -> ScoringPolicy:
    try:
        w = validate_weights(weights)
    except PolicyError as e:
        raise HTTPException(422, str(e))
    version = (db.scalar(select(func.max(ScoringPolicy.version)).where(ScoringPolicy.job_id == job.id)) or 0) + 1
    policy = ScoringPolicy(job_id=job.id, version=version, weights=w, created_by=user.id)
    db.add(policy)
    db.flush()
    audit.log(db, user.id, "set_policy", "job", job.id, version=version, weights=w)
    return policy


@router.post("", response_model=JobOut, status_code=201)
def create_job(body: JobIn, user: HRUser, db: DB):
    job = Job(owner_id=user.id, **body.model_dump())
    db.add(job)
    db.flush()
    audit.log(db, user.id, "create_job", "job", job.id, title=job.title)
    add_policy(db, job, DEFAULT_WEIGHTS, user)  # version 1
    db.commit()
    return job


@router.get("", response_model=list[JobOut])
def list_jobs(user: CurrentUser, db: DB):
    q = select(Job).order_by(Job.id.desc())
    if user.role == "candidate":
        q = q.where(Job.status == "published")
    elif user.role == "hr":
        q = q.where(Job.owner_id == user.id)
    return db.scalars(q).all()


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, user: CurrentUser, db: DB):
    job = db.get(Job, job_id)
    if not job or (user.role == "candidate" and job.status != "published"):
        raise HTTPException(404, "Job not found")
    if user.role == "hr" and job.owner_id != user.id:
        raise HTTPException(403, "You do not own this job")
    return job


@router.patch("/{job_id}", response_model=JobOut)
def update_job(job_id: int, body: JobUpdate, user: HRUser, db: DB):
    job = owned_job(db, job_id, user)
    if job.status == "closed":
        raise HTTPException(409, "A closed job cannot be edited")
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(job, k, v)
    audit.log(db, user.id, "update_job", "job", job.id, fields=sorted(changes))
    db.commit()
    return job


@router.post("/{job_id}/publish", response_model=JobOut)
def publish_job(job_id: int, user: HRUser, db: DB):
    job = owned_job(db, job_id, user)
    if job.status != "draft":
        raise HTTPException(409, f"Only a draft job can be published (status: {job.status})")
    job.status = "published"
    audit.log(db, user.id, "publish_job", "job", job.id)
    db.commit()
    return job


@router.post("/{job_id}/close", response_model=JobOut)
def close_job(job_id: int, user: HRUser, db: DB):
    job = owned_job(db, job_id, user)
    if job.status == "closed":
        raise HTTPException(409, "Job is already closed")
    job.status = "closed"
    audit.log(db, user.id, "close_job", "job", job.id)
    db.commit()
    return job


@router.post("/{job_id}/policies", response_model=PolicyOut, status_code=201)
def set_policy(job_id: int, body: PolicyIn, user: HRUser, db: DB):
    job = owned_job(db, job_id, user)
    policy = add_policy(db, job, body.weights, user)
    db.commit()
    return policy


@router.get("/{job_id}/policies", response_model=list[PolicyOut])
def list_policies(job_id: int, user: HRUser, db: DB):
    owned_job(db, job_id, user)
    return db.scalars(select(ScoringPolicy).where(ScoringPolicy.job_id == job_id)
                      .order_by(ScoringPolicy.version)).all()
