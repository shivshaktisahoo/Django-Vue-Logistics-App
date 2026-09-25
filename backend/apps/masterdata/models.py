from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models

from apps.core.models import TenantModel


class Mode(models.TextChoices):
    AIR = "air", "Air"
    OCEAN = "ocean", "Ocean"
    ROAD = "road", "Road"


class Party(TenantModel):
    """A company the forwarder deals with: a billing customer, a shipper, a consignee.

    `owner` puts a party in a customer's private address book: a customer-portal user
    sees only their own account and the parties they added, never other customers.
    """

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20, help_text="Short account code, e.g. NORDIC")
    is_customer = models.BooleanField(default=False, help_text="Billing account with portal access")
    is_shipper = models.BooleanField(default=False)
    is_consignee = models.BooleanField(default=False)
    owner = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="address_book",
        limit_choices_to={"is_customer": True},
    )
    contact_name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=2, help_text="ISO 3166-1 alpha-2")
    tax_id = models.CharField(max_length=40, blank=True, help_text="VAT / TRN / GSTIN / EORI")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "parties"
        constraints = [models.UniqueConstraint(fields=["org", "code"], name="uniq_party_code")]

    def __str__(self) -> str:
        return self.name


class Location(TenantModel):
    class Kind(models.TextChoices):
        SEAPORT = "seaport", "Seaport"
        AIRPORT = "airport", "Airport"
        INLAND = "inland", "Inland depot"
        WAREHOUSE = "warehouse", "Warehouse"
        CITY = "city", "City / door"

    code = models.CharField(
        max_length=10,
        validators=[
            RegexValidator(r"^[A-Z0-9]{3,10}$", "Use UN/LOCODE (e.g. AEJEA) or an internal code.")
        ],
        help_text="UN/LOCODE for ports and airports",
    )
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=2)
    latitude = models.DecimalField(
        max_digits=8, decimal_places=5, validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.DecimalField(
        max_digits=8, decimal_places=5, validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    timezone = models.CharField(max_length=50, default="UTC")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        constraints = [models.UniqueConstraint(fields=["org", "code"], name="uniq_location_code")]

    def __str__(self) -> str:
        return f"{self.code} · {self.name}"


class Carrier(TenantModel):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=10, help_text="SCAC (ocean), IATA prefix (air) or own code")
    mode = models.CharField(max_length=10, choices=Mode.choices)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=2, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["org", "code"], name="uniq_carrier_code")]

    def __str__(self) -> str:
        return self.name


class Vehicle(TenantModel):
    class Type(models.TextChoices):
        TRACTOR_TRAILER = "tractor_trailer", "Tractor + trailer"
        BOX_TRUCK = "box_truck", "Box truck"
        REEFER = "reefer", "Reefer"
        FLATBED = "flatbed", "Flatbed"
        VAN = "van", "Van"

    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE, related_name="vehicles")
    plate_number = models.CharField(max_length=20)
    vehicle_type = models.CharField(max_length=20, choices=Type.choices)
    capacity_kg = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["plate_number"]
        constraints = [
            models.UniqueConstraint(fields=["org", "plate_number"], name="uniq_vehicle_plate")
        ]

    def __str__(self) -> str:
        return self.plate_number


class Driver(TenantModel):
    carrier = models.ForeignKey(Carrier, on_delete=models.CASCADE, related_name="drivers")
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    license_number = models.CharField(max_length=40)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
