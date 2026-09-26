from django.conf import settings
from django.db import models

from apps.core.models import TenantModel


class ShipmentException(TenantModel):
    """Something about a shipment that needs a human: late, at risk, gone quiet, stuck.

    Rule-based kinds are raised *and cleared* by `detection.reconcile_shipment`, so the
    queue reflects reality without anyone closing stale alerts by hand. At most one
    unresolved exception exists per (shipment, kind); a recurring problem escalates
    the existing row instead of creating duplicates.
    """

    class Kind(models.TextChoices):
        ETA_OVERDUE = "eta_overdue", "Past ETA"
        ETA_AT_RISK = "eta_at_risk", "ETA at risk"
        STALE_TRACKING = "stale_tracking", "No recent tracking update"
        CUSTOMS_DWELL = "customs_dwell", "Long customs dwell"
        LONG_HOLD = "long_hold", "On hold too long"
        DELAY_REPORTED = "delay_reported", "Delay reported"

    class Severity(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"

    shipment = models.ForeignKey(
        "shipments.Shipment", on_delete=models.CASCADE, related_name="exceptions"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    severity = models.CharField(max_length=10, choices=Severity.choices)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)
    title = models.CharField(max_length=160)
    detail = models.CharField(max_length=500, blank=True)
    detected_at = models.DateTimeField()
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    resolution_note = models.CharField(max_length=500, blank=True)
    auto_resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-detected_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["shipment", "kind"],
                condition=~models.Q(status="resolved"),
                name="uniq_unresolved_exception_per_kind",
            )
        ]
        indexes = [models.Index(fields=["org", "status", "severity"], name="exc_org_status_sev")]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} · {self.shipment_id}"
