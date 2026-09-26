from django.conf import settings
from django.db import models

from apps.core.models import TenantModel


class ShipmentDocument(TenantModel):
    """A file attached to a shipment: POD, commercial invoice, B/L, customs entry…

    Bytes live in Postgres (`bytea`). For a demo that resets nightly and caps uploads
    at a few MB this needs zero extra infrastructure; production would swap in object
    storage (S3) behind the same service without touching the API. Downloads always
    go through an authenticated, tenant-scoped endpoint, never a public URL.
    """

    class DocType(models.TextChoices):
        POD = "pod", "Proof of delivery"
        COMMERCIAL_INVOICE = "commercial_invoice", "Commercial invoice"
        PACKING_LIST = "packing_list", "Packing list"
        BILL_OF_LADING = "bill_of_lading", "Bill of lading"
        AIR_WAYBILL = "air_waybill", "Air waybill"
        CMR = "cmr", "CMR consignment note"
        CUSTOMS = "customs", "Customs declaration"
        CERTIFICATE = "certificate", "Certificate (origin, phyto, DG)"
        OTHER = "other", "Other"

    shipment = models.ForeignKey(
        "shipments.Shipment", on_delete=models.CASCADE, related_name="documents"
    )
    trip = models.ForeignKey(
        "trips.Trip", on_delete=models.SET_NULL, null=True, blank=True, related_name="documents"
    )
    doc_type = models.CharField(max_length=20, choices=DocType.choices)
    file_name = models.CharField(max_length=200)
    content_type = models.CharField(max_length=60)
    size = models.PositiveIntegerField()
    sha256 = models.CharField(max_length=64)
    content = models.BinaryField()
    notes = models.CharField(max_length=255, blank=True)
    visible_to_customer = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["shipment", "-created_at"], name="doc_shipment_created")]

    def __str__(self) -> str:
        return f"{self.get_doc_type_display()} · {self.file_name}"
