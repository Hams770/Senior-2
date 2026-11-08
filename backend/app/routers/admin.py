from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from ..models import AuditLog
from ..schemas import AuditOut, ScoreIn
from ..scoring import PolicyError, compute_score
from ..security import DB, AdminUser, HRUser

router = APIRouter(prefix="/api", tags=["admin"])


@router.get("/audit", response_model=list[AuditOut])
def audit_log(admin: AdminUser, db: DB, limit: int = 100):
    return db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 500))).all()


@router.post("/scoring/preview")
def preview_score(body: ScoreIn, user: HRUser):
    """Lets the scoring screen show a score for given components and weights (no data is saved)."""
    try:
        return compute_score(body.components, body.weights)
    except (PolicyError, ValueError) as e:
        raise HTTPException(422, str(e))
