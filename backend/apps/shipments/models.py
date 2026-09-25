import secrets
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import TenantModel
from apps.masterdata.models import Mode

from .domain import EventCode, ShipmentStatus

TRACKING_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I: easy to read aloud


def new_tracking_number() -> str:
    return "CP" + "".join(secrets.choice(TRACKING_ALPHABET) for _ in range(10))


class Shipment(TenantModel):
    class ServiceType(models.TextChoices):
        FCL = "fcl", "FCL (full container)"
        LCL = "lcl", "LCL (consolidated)"
        AIR_STANDARD = "air_std", "Air standard"
        AIR_EXPRESS = "air_exp", "Air express"
        FTL = "ftl", "FTL (full truckload)"
        LTL = "ltl", "LTL (part load)"

    class Incoterm(models.TextChoices):
        EXW = "EXW", "EXW · Ex Works"
        FCA = "FCA", "FCA · Free Carrier"
        FOB = "FOB", "FOB · Free On Board"
        CFR = "CFR", "CFR · Cost and Freight"
        CIF = "CIF", "CIF · Cost, Insurance and Freight"
        CPT = "CPT", "CPT · Carriage Paid To"
        DAP = "DAP", "DAP · Delivered At Place"
        DDP = "DDP", "DDP · Delivered Duty Paid"

    reference = models.CharField(max_length=30, editable=False)
    tracking_number = models.CharField(
        max_length=12, unique=True, default=new_tracking_number, editable=False
    )
    status = models.CharField(
        max_length=20, choices=ShipmentStatus.choices, default=ShipmentStatus.DRAFT
    )
    held_from_status = models.CharField(max_length=20, blank=True, editable=False)

    mode = models.CharField(max_length=10, choices=Mode.choices)
    service_type = models.CharField(max_length=10, choices=ServiceType.choices)
    incoterm = models.CharField(max_length=3, choices=Incoterm.choices, default=Incoterm.FOB)

    customer = models.ForeignKey(
        "masterdata.Party", on_delete=models.PROTECT, related_name="shipments_billed"
    )
    shipper = models.ForeignKey(
        "masterdata.Party", on_delete=models.PROTECT, related_name="shipments_sent"
    )
    consignee = models.ForeignKey(
        "masterdata.Party", on_delete=models.PROTECT, related_name="shipments_received"
    )
    origin = models.ForeignKey(
        "masterdata.Location", on_delete=models.PROTECT, related_name="shipments_out"
    )
    destination = models.ForeignKey(
        "masterdata.Location", on_delete=models.PROTECT, related_name="shipments_in"
    )
    carrier = models.ForeignKey(
        "masterdata.Carrier",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="shipments",
    )

    etd = models.DateTimeField("Estimated departure", null=True, blank=True)
    eta = models.DateTimeField("Estimated arrival", null=True, blank=True)
    atd = models.DateTimeField("Actual departure", null=True, blank=True)
    ata = models.DateTimeField("Actual arrival / delivery", null=True, blank=True)

    house_bill = models.CharField(max_length=40, blank=True, help_text="HBL / HAWB number")
    master_bill = models.CharField(max_length=40, blank=True, help_text="MBL / MAWB number")
    voyage_number = models.CharField(max_length=40, blank=True, help_text="Vessel voyage / flight")
    customer_reference = models.CharField(max_length=60, blank=True, help_text="PO / order ref")

    commodity = models.CharField(max_length=150)
    hs_code = models.CharField(max_length=12, blank=True)
    declared_value = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)]
    )
    currency = models.CharField(max_length=3, default="USD")
    is_hazardous = models.BooleanField(default=False)
    is_temperature_controlled = models.BooleanField(default=False)
    special_instructions = models.TextField(blank=True)

    # Denormalised cargo totals, recomputed from packages by the service layer.
    total_packages = models.PositiveIntegerField(default=0)
    gross_weight_kg = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    volume_cbm = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal("0"))
    chargeable_weight_kg = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0")
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["org", "reference"], name="uniq_shipment_reference"),
            models.CheckConstraint(
                condition=~models.Q(origin=models.F("destination")),
                name="shipment_origin_ne_destination",
            ),
        ]
        indexes = [
            # The list page: "my org's shipments in status X, newest first".
            models.Index(fields=["org", "status", "-created_at"], name="shp_org_status_created"),
            # Customer portal and ETA-risk queries.
            models.Index(
                fields=["org", "customer", "-created_at"], name="shp_org_customer_created"
            ),
            models.Index(fields=["org", "eta"], name="shp_org_eta"),
        ]

    def __str__(self) -> str:
        return self.reference


class Package(models.Model):
    class Kind(models.TextChoices):
        CONTAINER = "container", "Container"
        PALLET = "pallet", "Pallet"
        CARTON = "carton", "Carton"
        CRATE = "crate", "Crate"
        DRUM = "drum", "Drum"
        PIECE = "piece", "Loose piece"

    class ContainerType(models.TextChoices):
        GP20 = "20GP", "20' General purpose"
        GP40 = "40GP", "40' General purpose"
        HC40 = "40HC", "40' High cube"
        HC45 = "45HC", "45' High cube"
        RF20 = "20RF", "20' Reefer"
        RF40 = "40RF", "40' Reefer"

    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="packages")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    container_type = models.CharField(max_length=4, choices=ContainerType.choices, blank=True)
    container_number = models.CharField(max_length=11, blank=True)
    seal_number = models.CharField(max_length=20, blank=True)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    description = models.CharField(max_length=150, blank=True)
    weight_kg = models.DecimalField(
        "Gross weight (kg, line total)",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    length_cm = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True)
    width_cm = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=7, decimal_places=1, null=True, blank=True)
    volume_cbm = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal("0"))
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self) -> str:
        return self.container_number or f"{self.quantity} × {self.get_kind_display()}"


class TrackingEvent(TenantModel):
    """One milestone in a shipment's life. Append-only; the timeline is ordered by
    `occurred_at` (when it happened), not `created_at` (when we learned about it)."""

    class Source(models.TextChoices):
        MANUAL = "manual", "Manual"
        SYSTEM = "system", "System"
        IMPORT = "import", "Bulk import"
        CARRIER = "carrier", "Carrier"
        GPS = "gps", "GPS"

    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="events")
    code = models.CharField(max_length=3, choices=EventCode.choices)
    description = models.CharField(max_length=255, blank=True)
    location = models.ForeignKey(
        "masterdata.Location", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    occurred_at = models.DateTimeField()
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.MANUAL)
    is_public = models.BooleanField(
        default=True, help_text="Visible to the customer and on the public tracking page"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-occurred_at", "-created_at"]
        indexes = [
            models.Index(fields=["shipment", "-occurred_at"], name="evt_shipment_occurred"),
            models.Index(fields=["org", "code", "-occurred_at"], name="evt_org_code_occurred"),
        ]

    def __str__(self) -> str:
        return f"{self.code} {self.shipment_id}"
