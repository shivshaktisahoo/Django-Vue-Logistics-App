from celery import shared_task

from . import detection


@shared_task
def scan_exceptions() -> dict:
    """Hourly: re-evaluate every in-flight shipment across all tenants."""
    return detection.scan()
