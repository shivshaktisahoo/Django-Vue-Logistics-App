from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.audit import services as audit
from apps.core.exceptions import DomainError
from apps.core.numbering import next_number
from apps.documents import services as documents
from apps.documents.models import ShipmentDocument
from apps.shipments import services as shipment_services
from apps.shipments.domain import ShipmentStatus as S
from apps.shipments.models import TrackingEvent

from .models import Trip, TripStop

CARRIER = TrackingEvent.Source.CARRIER


@transaction.atomic
def create_from_award(*, tender, bid, actor) -> Trip:
    shipment = tender.shipment
    pickup_at = tender.pickup_at
    deliver_at = min(tender.deliver_by, pickup_at + timedelta(hours=bid.transit_hours))
    trip = Trip.objects.create(
        org=tender.org,
        reference=next_number(org=tender.org, doc_type="trip", prefix="TRP"),
        carrier=bid.carrier,
        tender=tender,
        agreed_rate=bid.amount,
        currency=bid.currency,
        planned_start=pickup_at,
        planned_end=deliver_at,
        created_by=actor,
    )
    TripStop.objects.bulk_create(
        [
            TripStop(
                trip=trip,
                sequence=1,
                kind=TripStop.Kind.PICKUP,
                shipment=shipment,
                location=shipment.origin,
                planned_at=pickup_at,
            ),
            TripStop(
                trip=trip,
                sequence=2,
                kind=TripStop.Kind.DELIVERY,
                shipment=shipment,
                location=shipment.destination,
                planned_at=deliver_at,
            ),
        ]
    )
    return trip


def _lock(trip: Trip) -> Trip:
    return Trip.objects.select_for_update().get(pk=trip.pk)


@transaction.atomic
def assign(*, trip: Trip, vehicle, driver, actor) -> Trip:
    """Dispatch: put a truck and a driver from the carrier's own fleet on the trip."""
    trip = _lock(trip)
    if trip.status not in (Trip.Status.PLANNED, Trip.Status.DISPATCHED):
        raise DomainError("Vehicle and driver can only change before the trip starts.")
    if vehicle.carrier_id != trip.carrier_id or not vehicle.is_active:
        raise DomainError("Choose an active vehicle from the carrier's fleet.", field="vehicle")
    if driver.carrier_id != trip.carrier_id or not driver.is_active:
        raise DomainError("Choose an active driver from the carrier's roster.", field="driver")
    load_kg = sum(
        s.shipment.gross_weight_kg
        for s in trip.stops.select_related("shipment")
        if s.kind == TripStop.Kind.PICKUP
    )
    if load_kg > vehicle.capacity_kg:
        raise DomainError(
            f"{vehicle.plate_number} carries {vehicle.capacity_kg:,} kg; this load is {load_kg:,.0f} kg.",
            field="vehicle",
        )
    busy = (
        Trip.objects.filter(
            vehicle=vehicle, status__in=[Trip.Status.DISPATCHED, Trip.Status.IN_PROGRESS]
        )
        .exclude(pk=trip.pk)
        .first()
    )
    if busy:
        raise DomainError(
            f"{vehicle.plate_number} is already on trip {busy.reference}.", field="vehicle"
        )
    trip.vehicle, trip.driver, trip.status = vehicle, driver, Trip.Status.DISPATCHED
    trip.save(update_fields=["vehicle", "driver", "status", "updated_at"])
    audit.record(
        org=trip.org,
        actor=actor,
        action="trip.dispatched",
        entity=_primary_shipment(trip),
        summary=f"Trip {trip.reference} dispatched: {vehicle.plate_number}, driver {driver.name}",
    )
    return trip


def _primary_shipment(trip: Trip):
    return trip.stops.select_related("shipment").first().shipment


def _next_open_stop(trip: Trip) -> TripStop | None:
    return trip.stops.filter(completed_at__isnull=True).order_by("sequence").first()


def _check_order(trip: Trip, stop: TripStop) -> None:
    if trip.status not in (Trip.Status.DISPATCHED, Trip.Status.IN_PROGRESS):
        raise DomainError("Dispatch the trip (vehicle and driver) before running stops.")
    nxt = _next_open_stop(trip)
    if nxt is None or nxt.pk != stop.pk:
        raise DomainError(
            f"Complete stop {nxt.sequence if nxt else '—'} first.", code="stop_out_of_order"
        )


@transaction.atomic
def arrive(*, trip: Trip, stop: TripStop, actor, at=None) -> TripStop:
    trip = _lock(trip)
    _check_order(trip, stop)
    if stop.arrived_at:
        raise DomainError("Arrival is already recorded for this stop.")
    stop.arrived_at = at or timezone.now()
    stop.save(update_fields=["arrived_at"])
    shipment = stop.shipment
    if stop.kind == TripStop.Kind.DELIVERY and shipment.status in (S.IN_TRANSIT, S.AT_CUSTOMS):
        shipment_services.change_status(
            shipment=shipment,
            target=S.OUT_FOR_DELIVERY,
            actor=actor,
            occurred_at=stop.arrived_at,
            location=stop.location,
            note=f"Truck {trip.vehicle.plate_number} at consignee",
            source=CARRIER,
        )
    return stop


@transaction.atomic
def complete(
    *, trip: Trip, stop: TripStop, actor, receiver_name: str = "", pod_file=None, at=None
) -> TripStop:
    """Pickup: cargo loaded and departed. Delivery: signed for, with a POD document."""
    trip = _lock(trip)
    _check_order(trip, stop)
    now = at or timezone.now()
    shipment = stop.shipment
    if stop.kind == TripStop.Kind.DELIVERY:
        if not receiver_name.strip():
            raise DomainError(
                "Enter the name of the person who signed for the goods.", field="receiver_name"
            )
        if pod_file is not None:
            documents.upload(
                shipment=shipment,
                actor=actor,
                file=pod_file,
                doc_type=ShipmentDocument.DocType.POD,
                notes=f"Signed by {receiver_name.strip()}",
                trip=trip,
            )
        elif not ShipmentDocument.objects.filter(
            shipment=shipment, doc_type=ShipmentDocument.DocType.POD
        ).exists():
            raise DomainError("Attach the signed proof of delivery.", field="pod")

    if not stop.arrived_at:
        stop.arrived_at = now
    stop.completed_at, stop.receiver_name = now, receiver_name.strip()
    stop.save(update_fields=["arrived_at", "completed_at", "receiver_name"])

    if stop.kind == TripStop.Kind.PICKUP:
        if trip.status == Trip.Status.DISPATCHED:
            trip.status, trip.started_at = Trip.Status.IN_PROGRESS, now
            trip.save(update_fields=["status", "started_at", "updated_at"])
        plate = trip.vehicle.plate_number
        for target, note in (
            (S.PICKED_UP, f"Loaded on {plate}"),
            (S.IN_TRANSIT, f"{plate} departed"),
        ):
            shipment.refresh_from_db()
            if shipment.status in (S.BOOKED, S.PICKED_UP) and target != shipment.status:
                shipment_services.change_status(
                    shipment=shipment,
                    target=target,
                    actor=actor,
                    occurred_at=now,
                    location=stop.location,
                    note=note,
                    source=CARRIER,
                )
    else:
        shipment.refresh_from_db()
        if shipment.status in (S.IN_TRANSIT, S.AT_CUSTOMS):
            shipment_services.change_status(
                shipment=shipment,
                target=S.OUT_FOR_DELIVERY,
                actor=actor,
                occurred_at=now,
                location=stop.location,
                source=CARRIER,
            )
            shipment.refresh_from_db()
        if shipment.status == S.OUT_FOR_DELIVERY:
            shipment_services.change_status(
                shipment=shipment,
                target=S.DELIVERED,
                actor=actor,
                occurred_at=now,
                location=stop.location,
                note=f"Delivered, signed by {stop.receiver_name}",
                source=CARRIER,
            )
        if _next_open_stop(trip) is None:
            trip.status, trip.completed_at = Trip.Status.COMPLETED, now
            trip.save(update_fields=["status", "completed_at", "updated_at"])
    return stop


@transaction.atomic
def cancel(*, trip: Trip, actor, reason: str) -> Trip:
    trip = _lock(trip)
    if trip.status not in (Trip.Status.PLANNED, Trip.Status.DISPATCHED):
        raise DomainError("A trip that has started can't be cancelled; complete or re-plan it.")
    if not reason.strip():
        raise DomainError("Give a reason.", field="reason")
    trip.status, trip.notes = Trip.Status.CANCELLED, f"Cancelled: {reason.strip()}"
    trip.save(update_fields=["status", "notes", "updated_at"])
    shipment = _primary_shipment(trip)
    shipment.carrier = None
    shipment.save(update_fields=["carrier", "updated_at"])
    audit.record(
        org=trip.org,
        actor=actor,
        action="trip.cancelled",
        entity=shipment,
        summary=f"Trip {trip.reference} cancelled: {reason.strip()}",
    )
    return trip
