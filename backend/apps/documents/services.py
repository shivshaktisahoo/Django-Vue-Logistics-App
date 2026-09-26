import hashlib
import re

from django.db import transaction

from apps.audit import services as audit
from apps.core.exceptions import DomainError

from .models import ShipmentDocument

MAX_BYTES = 5 * 1024 * 1024

# Decide the type from the file's own bytes, not the client-supplied header.
SIGNATURES = [
    (b"%PDF-", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
]


def sniff(head: bytes) -> str | None:
    for magic, mime in SIGNATURES:
        if head.startswith(magic):
            return mime
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def _safe_name(name: str) -> str:
    name = name.replace("\\", "/").rsplit("/", 1)[-1]  # drop any client path
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .") or "document"
    return name[-200:]


@transaction.atomic
def upload(
    *,
    shipment,
    actor,
    file,
    doc_type: str,
    notes: str = "",
    visible_to_customer: bool = True,
    trip=None,
) -> ShipmentDocument:
    if file.size > MAX_BYTES:
        raise DomainError("Files can be at most 5 MB.", field="file")
    data = file.read()
    mime = sniff(data[:16])
    if mime is None:
        raise DomainError("Upload a PDF, JPEG, PNG or WebP file.", field="file")
    doc = ShipmentDocument.objects.create(
        org=shipment.org,
        shipment=shipment,
        trip=trip,
        doc_type=doc_type,
        file_name=_safe_name(file.name),
        content_type=mime,
        size=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        content=data,
        notes=notes,
        visible_to_customer=visible_to_customer,
        uploaded_by=actor,
    )
    audit.record(
        org=shipment.org,
        actor=actor,
        action="document.uploaded",
        entity=shipment,
        summary=f"Uploaded {doc.get_doc_type_display().lower()}: {doc.file_name}",
    )
    return doc


@transaction.atomic
def delete(*, doc: ShipmentDocument, actor) -> None:
    audit.record(
        org=doc.org,
        actor=actor,
        action="document.deleted",
        entity=doc.shipment,
        summary=f"Deleted {doc.get_doc_type_display().lower()}: {doc.file_name}",
    )
    doc.delete()
