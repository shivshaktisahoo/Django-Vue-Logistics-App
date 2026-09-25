from django.db import transaction
from django.utils import timezone

from .models import DocumentSeries


@transaction.atomic
def next_number(*, org, doc_type: str, prefix: str, width: int = 6) -> str:
    """Return the next reference, e.g. `SHP-2026-000123`.

    Must be called inside the transaction that saves the document, so a rollback
    also rolls the counter back and the sequence stays gap-free.
    """
    year = timezone.now().year
    series, _ = DocumentSeries.objects.get_or_create(
        org=org, doc_type=doc_type, year=year, defaults={"prefix": prefix}
    )
    series = DocumentSeries.objects.select_for_update().get(pk=series.pk)
    series.last_number += 1
    series.save(update_fields=["last_number"])
    return f"{series.prefix}-{year}-{series.last_number:0{width}d}"
