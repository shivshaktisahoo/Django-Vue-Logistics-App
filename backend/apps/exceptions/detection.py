"""Rule engine: which exceptions *should* be open for a shipment right now, and
reconciliation of that against what *is* open.

Rules are plain functions of (shipment, now, last event time). They're cheap enough to
run for every in-flight shipment on each scan, and idempotent: running twice changes
nothing, and a missed scan is caught up by the next one.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone

from apps.shipments.domain import TERMINAL_STATUSES, ShipmentStatus, eta_health
from apps.shipments.models import Shipment

from .models import ShipmentException as Exc

S = ShipmentStatus
SEVERITY_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}

# How long a moving shipment may go without any milestone before it's "gone quiet".
STALE_AFTER = {"air": timedelta(hours=24), "road": timedelta(hours=12), "ocean": timedelta(days=6)}
RULE_KINDS = {
    Exc.Kind.ETA_OVERDUE,
    Exc.Kind.ETA_AT_RISK,
    Exc.Kind.STALE_TRACKING,
    Exc.Kind.CUSTOMS_DWELL,
    Exc.Kind.LONG_HOLD,
}
# After a person resolves an exception, the same rule stays quiet for this long unless
# the situation gets worse; otherwise the next scan would re-raise what they just handled.
SUPPRESS_AFTER_MANUAL_RESOLVE = timedelta(hours=24)


def _suppressed(shipment: Shipment, kind: str, severity: str, now: datetime) -> bool:
    handled = (
        Exc.objects.filter(
            shipment=shipment,
            kind=kind,
            status=Exc.Status.RESOLVED,
            auto_resolved=False,
            resolved_at__gte=now - SUPPRESS_AFTER_MANUAL_RESOLVE,
        )
        .order_by("-resolved_at")
        .values_list("severity", flat=True)
        .first()
    )
    return handled is not None and SEVERITY_RANK[severity] <= SEVERITY_RANK[handled]


@dataclass(frozen=True)
class Finding:
    kind: str
    severity: str
    title: str
    detail: str


def _hours(delta: timedelta) -> int:
    return int(delta.total_seconds() // 3600)


def _age(delta: timedelta) -> str:
    h = _hours(delta)
    return f"{h // 24} d {h % 24} h" if h >= 24 else f"{h} h"


def evaluate(
    shipment: Shipment, now: datetime, last_event_at: datetime | None, status_since: datetime | None
) -> list[Finding]:
    findings: list[Finding] = []
    route = f"{shipment.origin.code} → {shipment.destination.code}"

    health = eta_health(shipment.status, shipment.eta, now)
    if health == "late":
        late = now - shipment.eta
        severity = (
            "critical"
            if late > timedelta(hours=72)
            else "high"
            if late > timedelta(hours=24)
            else "medium"
        )
        findings.append(
            Finding(
                Exc.Kind.ETA_OVERDUE,
                severity,
                f"{_age(late)} past ETA, not yet delivered",
                f"{route} was due {shipment.eta:%d %b %H:%M} UTC; status is {S(shipment.status).label.lower()}.",
            )
        )
    elif health == "risk":
        findings.append(
            Finding(
                Exc.Kind.ETA_AT_RISK,
                "medium",
                f"Due in {_age(shipment.eta - now)} but still {S(shipment.status).label.lower()}",
                f"{route}: cargo has not reached the destination hub.",
            )
        )

    if shipment.status in (S.PICKED_UP, S.IN_TRANSIT) and last_event_at:
        quiet = now - last_event_at
        limit = STALE_AFTER[shipment.mode]
        if quiet > limit:
            findings.append(
                Finding(
                    Exc.Kind.STALE_TRACKING,
                    "medium" if quiet > limit * 2 else "low",
                    f"No tracking update for {_age(quiet)}",
                    f"Expected a milestone at least every {_age(limit)} for {shipment.mode} freight. Chase the carrier.",
                )
            )

    if shipment.status == S.AT_CUSTOMS and status_since:
        dwell = now - status_since
        if dwell > timedelta(hours=48):
            findings.append(
                Finding(
                    Exc.Kind.CUSTOMS_DWELL,
                    "high" if dwell > timedelta(hours=96) else "medium",
                    f"In customs for {_age(dwell)}",
                    "Check for inspection, missing documents or unpaid duties.",
                )
            )

    if shipment.status == S.ON_HOLD and status_since:
        held = now - status_since
        if held > timedelta(hours=24):
            findings.append(
                Finding(
                    Exc.Kind.LONG_HOLD,
                    "high" if held > timedelta(hours=72) else "medium",
                    f"On hold for {_age(held)}",
                    "A hold should be released or escalated within a day.",
                )
            )
    return findings


@transaction.atomic
def reconcile_shipment(
    shipment: Shipment, *, now: datetime | None = None, last_event_at=None, status_since=None
) -> dict:
    """Open, escalate or auto-resolve rule-based exceptions for one shipment."""
    now = now or timezone.now()
    if last_event_at is None or status_since is None:
        last_event_at, status_since = _event_times(shipment)
    open_rows = {
        e.kind: e
        for e in Exc.objects.select_for_update()
        .filter(shipment=shipment)
        .exclude(status=Exc.Status.RESOLVED)
    }

    stats = {"opened": 0, "escalated": 0, "resolved": 0}
    if shipment.status in TERMINAL_STATUSES:
        for row in open_rows.values():
            _auto_resolve(row, now, f"Shipment {S(shipment.status).label.lower()}.")
            stats["resolved"] += 1
        return stats

    findings = {f.kind: f for f in evaluate(shipment, now, last_event_at, status_since)}
    for kind, row in open_rows.items():
        if kind in RULE_KINDS and kind not in findings:
            _auto_resolve(row, now, "Condition cleared.")
            stats["resolved"] += 1
    for kind, f in findings.items():
        row = open_rows.get(kind)
        if row is None:
            if _suppressed(shipment, kind, f.severity, now):
                continue
            Exc.objects.create(
                org_id=shipment.org_id,
                shipment=shipment,
                kind=kind,
                severity=f.severity,
                title=f.title,
                detail=f.detail,
                detected_at=now,
            )
            stats["opened"] += 1
        else:
            escalated = SEVERITY_RANK[f.severity] > SEVERITY_RANK[row.severity]
            row.title, row.detail = f.title, f.detail
            if escalated:
                row.severity = f.severity
                # An escalation needs fresh eyes even if someone acknowledged it earlier.
                row.status, row.acknowledged_at = Exc.Status.OPEN, None
                stats["escalated"] += 1
            row.save(
                update_fields=[
                    "title",
                    "detail",
                    "severity",
                    "status",
                    "acknowledged_at",
                    "updated_at",
                ]
            )
    return stats


def _auto_resolve(row: Exc, now, note: str) -> None:
    row.status, row.resolved_at, row.auto_resolved, row.resolution_note = (
        Exc.Status.RESOLVED,
        now,
        True,
        note,
    )
    row.save(
        update_fields=["status", "resolved_at", "auto_resolved", "resolution_note", "updated_at"]
    )


def _event_times(shipment: Shipment):
    events = shipment.events.all()
    last = events.aggregate(m=Max("occurred_at"))["m"]
    code = {
        S.AT_CUSTOMS: "CUS",
        S.ON_HOLD: "HLD",
    }.get(shipment.status)
    since = events.filter(code=code).aggregate(m=Max("occurred_at"))["m"] if code else None
    return last, since


def scan(*, org=None, now: datetime | None = None) -> dict:
    """Reconcile every shipment that is still moving or has something unresolved."""
    now = now or timezone.now()
    unresolved = Exc.objects.exclude(status=Exc.Status.RESOLVED).values("shipment_id")
    qs = (
        Shipment.objects.select_related("origin", "destination")
        .exclude(status=S.DRAFT)
        .filter(~Q(status__in=TERMINAL_STATUSES) | Q(pk__in=unresolved))
    )
    if org is not None:
        qs = qs.filter(org=org)
    totals = {"scanned": 0, "opened": 0, "escalated": 0, "resolved": 0}
    for shipment in qs.iterator(chunk_size=200):
        stats = reconcile_shipment(shipment, now=now)
        totals["scanned"] += 1
        for key, value in stats.items():
            totals[key] += value
    return totals
