from sqlalchemy.orm import Session

from .models import AuditLog


def log(db: Session, actor_id: int | None, action: str, entity: str, entity_id: int | None, **detail) -> None:
    """FR-22. Added to the same transaction as the change, so both commit or neither does."""
    db.add(AuditLog(actor_id=actor_id, action=action, entity=entity, entity_id=entity_id, detail=detail))
