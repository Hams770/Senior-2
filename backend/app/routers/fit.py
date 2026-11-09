"""FR-09: fit prediction for each application, shown to HR as evidence (never part of the score or a decision)."""
from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from .. import audit, fit_model
from ..models import Application, FitPrediction, Job, now
from ..security import DB, HRUser
from .applications import hr_application

router = APIRouter(prefix="/api", tags=["fit classifier"])


def cv_text(app: Application, doc=None) -> str | None:
    doc = doc or app.cv
    return (doc.corrected_text or doc.extracted_text) if doc else None


def fit_view(p: FitPrediction | None) -> dict | None:
    if p is None:
        return None
    probs = dict(zip(fit_model.LABELS, (p.p_no, p.p_potential, p.p_good)))
    return {"label": max(probs, key=probs.get), "probabilities": probs, "needs_hr_review": p.needs_hr_review,
            "model_version": p.model_version, "created_at": p.created_at}


def latest_fit(db, app_id: int) -> FitPrediction | None:
    return db.scalar(select(FitPrediction).where(FitPrediction.application_id == app_id))


def run_fit(db, app: Application, doc=None) -> FitPrediction | None:
    """Predict and store; returns None (and stores nothing) when there is no CV text or no classifier."""
    text = cv_text(app, doc)
    if not text:
        return None
    try:
        r = fit_model.predict(text, fit_model.job_text(db.get(Job, app.job_id)))
    except Exception as e:  # the application must never fail because of the classifier
        fit_model.log.warning("No fit prediction for application %s: %s", app.id, e)
        return None
    p = latest_fit(db, app.id) or FitPrediction(application_id=app.id)
    p.model_version, p.needs_hr_review, p.created_at = r.model_version, r.needs_hr_review, now()
    p.p_no, p.p_potential, p.p_good = (r.probabilities[k] for k in fit_model.LABELS)
    db.add(p)
    return p


@router.get("/model/status")
def model_status(user: HRUser):
    return fit_model.status()


@router.get("/applications/{app_id}/fit")
def get_fit(app_id: int, user: HRUser, db: DB):
    app = hr_application(db, app_id, user)
    return {"prediction": fit_view(latest_fit(db, app.id)), "classifier": fit_model.status()}


@router.post("/applications/{app_id}/fit")
def rerun_fit(app_id: int, user: HRUser, db: DB):
    app = hr_application(db, app_id, user)
    if not cv_text(app):
        raise HTTPException(409, "There is no CV text to analyse; correct the CV in CV Screening first")
    st = fit_model.status()
    if not st["available"]:
        raise HTTPException(503, f"The fit classifier is not available: {st['reason']}")
    p = run_fit(db, app)
    if p is None:
        raise HTTPException(503, "The fit classifier failed on this CV; see the server log")
    audit.log(db, user.id, "fit_prediction", "application", app.id, model=p.model_version,
              needs_hr_review=p.needs_hr_review)
    db.commit()
    return {"prediction": fit_view(p), "classifier": st}
