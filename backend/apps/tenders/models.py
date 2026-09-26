from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TenantModel
from apps.masterdata.models import Vehicle


class Tender(TenantModel):
    """A spot RFQ: "who will move this load, from A to B, on this truck type, for how much?"

    Carriers are invited explicitly; bidding is sealed (a carrier only ever sees its own
    bid). The tender closes at `closes_at`, then operations award one bid, which books the
    carrier on the shipment and creates the trip.
    """

    class Status(models.TextChoices):
        OPEN = "open", "Open for bids"
        CLOSED = "closed", "Closed · awaiting award"
        AWARDED = "awarded", "Awarded"
        CANCELLED = "cancelled", "Cancelled"

    reference = models.CharField(max_length=30, editable=False)
    shipment = models.ForeignKey(
        "shipments.Shipment", on_delete=models.CASCADE, related_name="tenders"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    vehicle_type = models.CharField(max_length=20, choices=Vehicle.Type.choices)
    pickup_at = models.DateTimeField()
    deliver_by = models.DateTimeField()
    closes_at = models.DateTimeField(help_text="Bidding deadline")
    target_rate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Internal budget; never shown to carriers",
    )
    currency = models.CharField(max_length=3, default="USD")
    notes = models.TextField(blank=True, help_text="Shown to invited carriers")
    invited_carriers = models.ManyToManyField(
        "masterdata.Carrier", related_name="tender_invitations"
    )
    awarded_bid = models.ForeignKey(
        "tenders.Bid", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    cancel_reason = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["org", "reference"], name="uniq_tender_reference"),
            # One live tender per shipment at a time.
            models.UniqueConstraint(
                fields=["shipment"],
                condition=models.Q(status__in=["open", "closed", "awarded"]),
                name="uniq_live_tender_per_shipment",
            ),
        ]
        indexes = [
            models.Index(fields=["org", "status", "closes_at"], name="tnd_org_status_closes")
        ]

    def __str__(self) -> str:
        return self.reference


class Bid(TenantModel):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        WITHDRAWN = "withdrawn", "Withdrawn"
        WON = "won", "Won"
        LOST = "lost", "Not selected"

    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name="bids")
    carrier = models.ForeignKey("masterdata.Carrier", on_delete=models.CASCADE, related_name="bids")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(1)])
    currency = models.CharField(max_length=3)
    transit_hours = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    notes = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SUBMITTED)
    revision = models.PositiveSmallIntegerField(default=1)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta:
        ordering = ["amount"]
        constraints = [
            models.UniqueConstraint(fields=["tender", "carrier"], name="uniq_bid_per_carrier")
        ]

    def __str__(self) -> str:
        return f"{self.carrier} {self.amount} {self.currency}"
