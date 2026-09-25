from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit import services as audit
from apps.core.exceptions import DomainError
from apps.core.numbering import next_number

from . import domain
from .domain import EventCode, ShipmentStatus
from .models import Package, Shipment, TrackingEvent

S = ShipmentStatus

SHIPMENT_FIELDS = {
    "mode",
    "service_type",
    "incoterm",
    "customer",
    "shipper",
    "consignee",
    "origin",
    "destination",
    "carrier",
    "etd",
    "eta",
    "house_bill",
    "master_bill",
    "voyage_number",
    "customer_reference",
    "commodity",
    "hs_code",
    "declared_value",
    "currency",
    "is_hazardous",
    "is_temperature_controlled",
    "special_instructions",
}

MODE_SERVICES = {
    "ocean": {Shipment.ServiceType.FCL, Shipment.ServiceType.LCL},
    "air": {Shipment.ServiceType.AIR_STANDARD, Shipment.ServiceType.AIR_EXPRESS},
    "road": {Shipment.ServiceType.FTL, Shipment.ServiceType.LTL},
}

# Milestones that are only written by a status change, never added by hand.
STATUS_ONLY_CODES = frozenset(domain.STATUS_EVENT.values()) | {EventCode.RESUMED}


# ---------------------------------------------------------------- validation


def _validate_header(data: dict) -> None:
    mode, service = data.get("mode"), data.get("service_type")
    if mode and service and service not in MODE_SERVICES[mode]:
        raise DomainError(
            f"{Shipment.ServiceType(service).label} is not a {mode} service.", field="service_type"
        )
    if data.get("origin") and data.get("origin") == data.get("destination"):
        raise DomainError("Origin and destination must differ.", field="destination")
    etd, eta = data.get("etd"), data.get("eta")
    if etd and eta and eta <= etd:
        raise DomainError("ETA must be after ETD.", field="eta")
    carrier = data.get("carrier")
    if carrier and mode and carrier.mode != mode:
        raise DomainError(f"{carrier} is a {carrier.mode} carrier.", field="carrier")


def _validate_packages(mode: str, service_type: str, packages: list[dict]) -> None:
    if not packages:
        raise DomainError("Add at least one package or container.", field="packages")
    for i, p in enumerate(packages, start=1):
        is_container = p["kind"] == Package.Kind.CONTAINER
        if is_container and mode != "ocean":
            raise DomainError(
                f"Line {i}: containers are only used for ocean freight.", field="packages"
            )
        if is_container and not p.get("container_type"):
            raise DomainError(f"Line {i}: choose a container type.", field="packages")
        number = (p.get("container_number") or "").replace(" ", "").upper()
        if number:
            if not is_container:
                raise DomainError(
                    f"Line {i}: only containers carry a container number.", field="packages"
                )
            if not domain.is_valid_container_number(number):
                raise DomainError(
                    f"Line {i}: {number} is not a valid ISO 6346 container number (check digit).",
                    field="packages",
                )
            if p.get("quantity", 1) != 1:
                raise DomainError(
                    f"Line {i}: a numbered container must have quantity 1.", field="packages"
                )
    if service_type == Shipment.ServiceType.FCL and not any(
        p["kind"] == Package.Kind.CONTAINER for p in packages
    ):
        raise DomainError("An FCL shipment needs at least one container line.", field="packages")


def _write_packages(shipment: Shipment, packages: list[dict]) -> None:
    shipment.packages.all().delete()
    rows = []
    for position, p in enumerate(packages):
        row = Package(shipment=shipment, position=position, **p)
        row.container_number = (row.container_number or "").replace(" ", "").upper()
        row.volume_cbm = domain.volume_cbm(row.length_cm, row.width_cm, row.height_cm, row.quantity)
        rows.append(row)
    Package.objects.bulk_create(rows)
    recalculate_totals(shipment, rows)


def recalculate_totals(shipment: Shipment, packages: list[Package] | None = None) -> None:
    packages = packages if packages is not None else list(shipment.packages.all())
    shipment.total_packages = sum(p.quantity for p in packages)
    shipment.gross_weight_kg = sum((p.weight_kg for p in packages), Decimal("0"))
    shipment.volume_cbm = sum((p.volume_cbm for p in packages), Decimal("0"))
    shipment.chargeable_weight_kg = domain.chargeable_weight(
        shipment.mode, shipment.gross_weight_kg, shipment.volume_cbm
    )
    shipment.save(
        update_fields=[
            "total_packages",
            "gross_weight_kg",
            "volume_cbm",
            "chargeable_weight_kg",
            "updated_at",
        ]
    )


# ---------------------------------------------------------------- commands


@transaction.atomic
def create_shipment(*, org, actor, packages: list[dict], book: bool = False, **data) -> Shipment:
    data = {k: v for k, v in data.items() if k in SHIPMENT_FIELDS}
    _validate_header(data)
    _validate_packages(data["mode"], data["service_type"], packages)

    shipment = Shipment(org=org, created_by=actor, **data)
    shipment.reference = next_number(org=org, doc_type="shipment", prefix="SHP")
    shipment.full_clean(exclude=["reference", "tracking_number"])
    shipment.save()
    _write_packages(shipment, packages)
    audit.record(
        org=org,
        actor=actor,
        action="shipment.created",
        entity=shipment,
        summary=f"Created {shipment.get_mode_display().lower()} shipment "
        f"{shipment.origin.code} → {shipment.destination.code}",
    )
    if book:
        change_status(shipment=shipment, target=S.BOOKED, actor=actor)
    return shipment


@transaction.atomic
def update_shipment(
    *, shipment: Shipment, actor, packages: list[dict] | None = None, **data
) -> Shipment:
    shipment = Shipment.objects.select_for_update().get(pk=shipment.pk)
    data = {k: v for k, v in data.items() if k in SHIPMENT_FIELDS}
    if shipment.status not in domain.EDITABLE_STATUSES:
        # Once cargo moves, only references and schedule can still change.
        locked = set(data) - {
            "eta",
            "house_bill",
            "master_bill",
            "voyage_number",
            "special_instructions",
        }
        if locked or packages is not None:
            raise DomainError(
                "Route, parties and cargo are locked once the shipment has been picked up.",
                code="shipment_locked",
            )
    merged = {f: getattr(shipment, f) for f in SHIPMENT_FIELDS} | data
    _validate_header(merged)
    if packages is not None:
        _validate_packages(merged["mode"], merged["service_type"], packages)

    changes = audit.diff(shipment, data)
    for field, value in data.items():
        setattr(shipment, field, value)
    shipment.full_clean(exclude=["reference", "tracking_number"])
    shipment.save()
    if packages is not None:
        _write_packages(shipment, packages)
        changes["packages"] = ["updated", f"{len(packages)} line(s)"]
    elif "mode" in data:
        recalculate_totals(shipment)
    if changes:
        audit.record(
            org=shipment.org,
            actor=actor,
            action="shipment.updated",
            entity=shipment,
            summary="Updated " + ", ".join(sorted(changes)),
            changes=changes,
        )
    return shipment


RESUME = "resume"


@transaction.atomic
def change_status(
    *,
    shipment: Shipment,
    target: str,
    actor,
    occurred_at: datetime | None = None,
    location=None,
    note: str = "",
    source: str = TrackingEvent.Source.MANUAL,
) -> Shipment:
    """Move a shipment through its lifecycle and write the matching milestone.

    Row-locked so two coordinators clicking at once can't both apply a transition.
    `target="resume"` releases a hold back to the status it was held from.
    """
    shipment = Shipment.objects.select_for_update().get(pk=shipment.pk)
    current = shipment.status
    occurred_at = occurred_at or timezone.now()
    if occurred_at > timezone.now() + timedelta(minutes=5):
        raise DomainError("A milestone can't be in the future.", field="occurred_at")

    if target == RESUME:
        if current != S.ON_HOLD:
            raise DomainError("Only a shipment on hold can be resumed.", code="invalid_transition")
        target, code = shipment.held_from_status, EventCode.RESUMED
        shipment.held_from_status = ""
    else:
        if not domain.can_transition(current, target):
            raise DomainError(
                f"Can't move a shipment from {S(current).label} to {S(target).label}.",
                code="invalid_transition",
            )
        code = domain.STATUS_EVENT[target]
        if target == S.ON_HOLD:
            if not note:
                raise DomainError("Give a reason for the hold.", field="note")
            shipment.held_from_status = current
        if target == S.CANCELLED and not note:
            raise DomainError("Give a reason for the cancellation.", field="note")

    shipment.status = target
    if target == S.IN_TRANSIT and shipment.atd is None:
        shipment.atd = occurred_at
    if target == S.DELIVERED:
        shipment.ata = occurred_at
    shipment.save(update_fields=["status", "held_from_status", "atd", "ata", "updated_at"])

    TrackingEvent.objects.create(
        org=shipment.org,
        shipment=shipment,
        code=code,
        description=note or EventCode(code).label,
        location=location or _default_location(shipment, target),
        occurred_at=occurred_at,
        source=source,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    audit.record(
        org=shipment.org,
        actor=actor,
        action="shipment.status_changed",
        entity=shipment,
        summary=f"{S(current).label} → {S(target).label}" + (f": {note}" if note else ""),
        changes={"status": [current, target]},
    )
    return shipment


def _default_location(shipment: Shipment, status: str):
    if status in {S.BOOKED, S.PICKED_UP, S.IN_TRANSIT}:
        return shipment.origin
    if status in {S.AT_CUSTOMS, S.OUT_FOR_DELIVERY, S.DELIVERED}:
        return shipment.destination
    return None


@transaction.atomic
def add_event(
    *,
    shipment: Shipment,
    actor,
    code: str,
    occurred_at: datetime,
    location=None,
    description: str = "",
    is_public: bool = True,
    source: str = TrackingEvent.Source.MANUAL,
) -> TrackingEvent:
    """Record an informational milestone (gate-in, loaded, arrived, delay…)."""
    shipment.refresh_from_db(fields=["status"])
    if code in STATUS_ONLY_CODES:
        raise DomainError(
            f"{EventCode(code).label} is recorded by changing the shipment status.", field="code"
        )
    if shipment.status in (S.DRAFT, S.CANCELLED):
        raise DomainError("Milestones can only be added to booked shipments.")
    if occurred_at > timezone.now() + timedelta(minutes=5):
        raise DomainError("A milestone can't be in the future.", field="occurred_at")
    event = TrackingEvent.objects.create(
        org=shipment.org,
        shipment=shipment,
        code=code,
        description=description or EventCode(code).label,
        location=location,
        occurred_at=occurred_at,
        source=source,
        is_public=is_public,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    if code == EventCode.DELAYED:
        audit.record(
            org=shipment.org,
            actor=actor,
            action="shipment.delay_reported",
            entity=shipment,
            summary=description or "Delay reported",
        )
    return event
