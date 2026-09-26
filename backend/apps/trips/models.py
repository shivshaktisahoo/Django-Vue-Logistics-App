from django.conf import settings
from django.db import models

from apps.core.models import TenantModel


class Trip(TenantModel):
    """A truck's job: pickup and delivery stops, run by a carrier with its own vehicle
    and driver. Executing stops moves the linked shipments through their lifecycle."""

    class Status(models.TextChoices):
        PLANNED = "planned", "Planned"
        DISPATCHED = "dispatched", "Dispatched"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    reference = models.CharField(max_length=30, editable=False)
    carrier = models.ForeignKey(
        "masterdata.Carrier", on_delete=models.PROTECT, related_name="trips"
    )
    tender = models.ForeignKey(
        "tenders.Tender", on_delete=models.SET_NULL, null=True, blank=True, related_name="trips"
    )
    vehicle = models.ForeignKey(
        "masterdata.Vehicle", on_delete=models.PROTECT, null=True, blank=True, related_name="trips"
    )
    driver = models.ForeignKey(
        "masterdata.Driver", on_delete=models.PROTECT, null=True, blank=True, related_name="trips"
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PLANNED)
    agreed_rate = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="USD")
    planned_start = models.DateTimeField()
    planned_end = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta:
        ordering = ["-planned_start"]
        constraints = [
            models.UniqueConstraint(fields=["org", "reference"], name="uniq_trip_reference")
        ]
        indexes = [
            models.Index(fields=["org", "carrier", "status"], name="trip_org_carrier_status")
        ]

    def __str__(self) -> str:
        return self.reference


class TripStop(models.Model):
    class Kind(models.TextChoices):
        PICKUP = "pickup", "Pickup"
        DELIVERY = "delivery", "Delivery"

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="stops")
    sequence = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=10, choices=Kind.choices)
    shipment = models.ForeignKey(
        "shipments.Shipment", on_delete=models.PROTECT, related_name="trip_stops"
    )
    location = models.ForeignKey("masterdata.Location", on_delete=models.PROTECT, related_name="+")
    planned_at = models.DateTimeField()
    arrived_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    receiver_name = models.CharField(
        max_length=120, blank=True, help_text="Who signed for the goods"
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["sequence"]
        constraints = [
            models.UniqueConstraint(fields=["trip", "sequence"], name="uniq_stop_sequence")
        ]

    def __str__(self) -> str:
        return f"{self.trip_id} #{self.sequence} {self.kind}"
