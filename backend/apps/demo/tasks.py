from celery import shared_task

from .seed import seed_demo


@shared_task
def reset_demo_workspace() -> str:
    """Nightly: rebuild the showcase so visitors always land on clean, realistic data."""
    return str(seed_demo(reset=True).id)
