from django.conf import settings
from django.db import models

from apps.core.models import TenantModel


class AuditEntry(TenantModel):
    """Append-only record of who changed what. Written only via `audit.services.record`."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    action = models.CharField(max_length=40)  # e.g. "shipment.created", "shipment.status_changed"
    entity_type = models.CharField(max_length=40)
    entity_id = models.UUIDField()
    entity_label = models.CharField(max_length=120, blank=True)
    summary = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(default=dict, blank=True)  # {"field": [old, new]}

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["org", "entity_type", "entity_id", "-created_at"])]
        verbose_name_plural = "audit entries"

    def __str__(self) -> str:
        return f"{self.action} {self.entity_label}"
