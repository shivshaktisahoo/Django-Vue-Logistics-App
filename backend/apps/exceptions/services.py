from django.db import transaction
from django.utils import timezone

from apps.audit import services as audit
from apps.core.exceptions import DomainError
from apps.organizations.models import Membership

from .models import ShipmentException as Exc


def _record(exc: Exc, actor, summary: str) -> None:
    # Logged against the shipment so its Activity tab tells the whole story.
    audit.record(
        org=exc.org,
        actor=actor,
        action=f"exception.{summary.split()[0].lower()}",
        entity=exc.shipment,
        summary=summary,
    )


@transaction.atomic
def acknowledge(*, exc: Exc, actor) -> Exc:
    if exc.status != Exc.Status.OPEN:
        raise DomainError("Only open exceptions can be acknowledged.")
    exc.status, exc.acknowledged_at = Exc.Status.ACKNOWLEDGED, timezone.now()
    if exc.assignee_id is None:
        exc.assignee = actor
    exc.save(update_fields=["status", "acknowledged_at", "assignee", "updated_at"])
    _record(exc, actor, f"Acknowledged “{exc.get_kind_display()}”")
    return exc


@transaction.atomic
def assign(*, exc: Exc, assignee_id, actor) -> Exc:
    if exc.status == Exc.Status.RESOLVED:
        raise DomainError("This exception is already resolved.")
    membership = (
        Membership.objects.filter(org=exc.org, user_id=assignee_id, is_active=True)
        .select_related("user")
        .first()
    )
    if membership is None or not membership.has_perm("exceptions.manage"):
        raise DomainError("Assign to an internal team member.", field="assignee")
    exc.assignee = membership.user
    exc.save(update_fields=["assignee", "updated_at"])
    _record(
        exc,
        actor,
        f"Assigned “{exc.get_kind_display()}” to {membership.user.full_name or membership.user.email}",
    )
    return exc


@transaction.atomic
def resolve(*, exc: Exc, actor, note: str) -> Exc:
    if exc.status == Exc.Status.RESOLVED:
        raise DomainError("This exception is already resolved.")
    if not note.strip():
        raise DomainError("Describe how it was resolved.", field="note")
    exc.status, exc.resolved_at, exc.resolved_by, exc.resolution_note = (
        Exc.Status.RESOLVED,
        timezone.now(),
        actor,
        note.strip(),
    )
    exc.save(
        update_fields=["status", "resolved_at", "resolved_by", "resolution_note", "updated_at"]
    )
    _record(exc, actor, f"Resolved “{exc.get_kind_display()}”: {note.strip()}")
    return exc


def raise_delay(*, shipment, description: str, occurred_at) -> Exc:
    """A carrier/ops-reported delay opens (or refreshes) a delay exception immediately."""
    exc, created = Exc.objects.get_or_create(
        shipment=shipment,
        kind=Exc.Kind.DELAY_REPORTED,
        status__in=[Exc.Status.OPEN, Exc.Status.ACKNOWLEDGED],
        defaults={
            "org_id": shipment.org_id,
            "severity": Exc.Severity.MEDIUM,
            "title": "Delay reported",
            "detail": description[:500],
            "detected_at": occurred_at,
            "status": Exc.Status.OPEN,
        },
    )
    if not created:
        exc.detail, exc.status, exc.acknowledged_at = description[:500], Exc.Status.OPEN, None
        exc.save(update_fields=["detail", "status", "acknowledged_at", "updated_at"])
    return exc
