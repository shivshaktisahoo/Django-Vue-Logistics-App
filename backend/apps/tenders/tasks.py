from celery import shared_task

from . import services


@shared_task
def close_expired_tenders() -> int:
    """Backstop for the lazy close done on every tender read."""
    return services.close_expired()
