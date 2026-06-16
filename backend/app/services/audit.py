from sqlalchemy.orm import Session
from app.models.models import AuditLog


def audit(db: Session, entity: str, action: str, entity_id=None, detail=None,
          actor: str = "system", commit: bool = True):
    log = AuditLog(entity=entity, entity_id=entity_id, action=action,
                   detail=detail, actor=actor)
    db.add(log)
    if commit:
        db.commit()
    return log
