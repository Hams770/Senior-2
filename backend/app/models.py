"""Database tables, one class per entity of the ERD (report Section 4)."""
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))  # admin | hr | candidate
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    required_skills: Mapped[list] = mapped_column(JSON, default=list)
    level: Mapped[str] = mapped_column(String(50), default="")
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | published | closed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    policies: Mapped[list["ScoringPolicy"]] = relationship(back_populates="job", order_by="ScoringPolicy.version")


class ScoringPolicy(Base):
    """FR-04: each change of weights creates a new version; old versions are kept."""
    __tablename__ = "scoring_policies"
    __table_args__ = (UniqueConstraint("job_id", "version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    version: Mapped[int] = mapped_column(Integer)
    weights: Mapped[dict] = mapped_column(JSON)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    job: Mapped[Job] = relationship(back_populates="policies")


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("job_id", "candidate_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    candidate_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # submitted -> assessment -> decided -> hired | not_hired | withdrawn
    status: Mapped[str] = mapped_column(String(30), default="submitted")
    hr_ratings: Mapped[dict] = mapped_column(JSON, default=dict)  # exp, edu, soft (0-100) rated by HR from CV evidence
    final_outcome: Mapped[str | None] = mapped_column(String(30), nullable=True)  # FR-20
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    cv: Mapped["CVDocument"] = relationship(back_populates="application", uselist=False)


class CVDocument(Base):
    __tablename__ = "cv_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), unique=True)
    original_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))
    sha256: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    parse_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | parsed | failed | corrected
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # parser output, never overwritten
    sections: Mapped[dict] = mapped_column(JSON, default=dict)
    corrected_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # FR-08 HR correction
    skills: Mapped[list["ExtractedSkill"]] = relationship(order_by="ExtractedSkill.skill")
    application: Mapped[Application] = relationship(back_populates="cv")


class ExtractedSkill(Base):
    __tablename__ = "extracted_skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    cv_id: Mapped[int] = mapped_column(ForeignKey("cv_documents.id"))
    skill: Mapped[str] = mapped_column(String(100))
    source_excerpt: Mapped[str] = mapped_column(Text)  # FR-07
    section: Mapped[str] = mapped_column(String(30), default="")
    origin: Mapped[str] = mapped_column(String(10), default="parser")  # parser | hr
    active: Mapped[bool] = mapped_column(Boolean, default=True)  # parser rows are kept but deactivated on correction


class FitPrediction(Base):
    __tablename__ = "fit_predictions"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), unique=True)
    model_version: Mapped[str] = mapped_column(String(100))
    p_no: Mapped[float] = mapped_column(Float)
    p_potential: Mapped[float] = mapped_column(Float)
    p_good: Mapped[float] = mapped_column(Float)
    needs_hr_review: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Assessment(Base):
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    skill: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(20))  # mcq | practical
    title: Mapped[str] = mapped_column(String(255), default="")
    content: Mapped[dict] = mapped_column(JSON, default=dict)  # mcq: questions + answer key; practical: prompt + rubric
    time_limit_min: Mapped[int] = mapped_column(Integer, default=30)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id"))
    __table_args__ = (UniqueConstraint("assessment_id", "application_id"),)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    # assigned | in_progress | submitted (awaiting HR rubric) | graded | expired (not assessed)
    status: Mapped[str] = mapped_column(String(20), default="assigned")
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    points: Mapped[dict] = mapped_column(JSON, default=dict)  # practical: rubric points given by HR
    grader_notes: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100; None = not assessed (D1)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    graded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assessment: Mapped[Assessment] = relationship()


class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    policy_id: Mapped[int] = mapped_column(ForeignKey("scoring_policies.id"))
    stage: Mapped[str] = mapped_column(String(20))  # provisional | final
    components: Mapped[dict] = mapped_column(JSON)
    score: Mapped[float] = mapped_column(Float)  # stored unrounded
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), unique=True)
    decided_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    outcome: Mapped[str] = mapped_column(String(30))  # advance | hold | reject
    reason: Mapped[str] = mapped_column(Text)
    evaluation_id: Mapped[int | None] = mapped_column(ForeignKey("evaluations.id"), nullable=True)  # evidence seen
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"))
    draft: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20), default="template")  # template | llm
    model: Mapped[str] = mapped_column(String(100), default="")
    summary: Mapped[dict] = mapped_column(JSON, default=dict)  # the anonymised input that produced the draft
    approved_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | approved | released | discarded
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    """FR-22: one row for every change to a job, evaluation, decision or feedback."""
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(50))
    entity: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
