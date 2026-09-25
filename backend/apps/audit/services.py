from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from django.db import models

from .models import AuditEntry


def _jsonable(value):
    if isinstance(value, models.Model):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal | UUID):
        return str(value)
    return value


def diff(instance: models.Model, data: dict) -> dict:
    """{"field": [old, new]} for each field in `data` whose value actually changes."""
    changes = {}
    for field, new in data.items():
        old = getattr(instance, field, None)
        if old != new:
            changes[field] = [_jsonable(old), _jsonable(new)]
    return changes


def record(
    *, org, actor, action: str, entity, summary: str = "", changes: dict | None = None
) -> AuditEntry:
    return AuditEntry.objects.create(
        org=org,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        entity_type=entity._meta.model_name,
        entity_id=entity.pk,
        entity_label=str(entity)[:120],
        summary=summary[:255],
        changes=changes or {},
    )
