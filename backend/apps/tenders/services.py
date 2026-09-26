from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.audit import services as audit
from apps.core.exceptions import DomainError
from apps.core.numbering import next_number
from apps.shipments.domain import ShipmentStatus

from .models import Bid, Tender

MIN_BIDDING_WINDOW = timedelta(minutes=15)
MAX_BIDDING_WINDOW = timedelta(days=14)


def close_expired(*, org=None, now=None) -> int:
    """Close tenders whose deadline has passed.

    Called lazily before tenders are read (and hourly by beat), so the free-tier
    deployment doesn't need a frequent scheduler that keeps the database awake.
    """
    now = now or timezone.now()
    qs = Tender.objects.filter(status=Tender.Status.OPEN, closes_at__lte=now)
    if org is not None:
        qs = qs.filter(org=org)
    return qs.update(status=Tender.Status.CLOSED, updated_at=now)


@transaction.atomic
def create_tender(
    *,
    shipment,
    actor,
    carriers,
    vehicle_type: str,
    pickup_at,
    deliver_by,
    closes_at,
    target_rate: Decimal | None = None,
    notes: str = "",
) -> Tender:
    now = timezone.now()
    if shipment.mode != "road":
        raise DomainError(
            "Spot tenders are for road legs; book ocean and air with the line directly."
        )
    if shipment.status not in (ShipmentStatus.DRAFT, ShipmentStatus.BOOKED):
        raise DomainError("Tender a shipment before it's picked up.")
    if Tender.objects.filter(shipment=shipment, status__in=["open", "closed", "awarded"]).exists():
        raise DomainError("This shipment already has a live tender.")
    if not carriers:
        raise DomainError("Invite at least one carrier.", field="carriers")
    wrong = [c for c in carriers if c.mode != "road" or not c.is_active]
    if wrong:
        raise DomainError(f"{wrong[0]} isn't an active road carrier.", field="carriers")
    if not (now + MIN_BIDDING_WINDOW <= closes_at <= now + MAX_BIDDING_WINDOW):
        raise DomainError("Give carriers between 15 minutes and 14 days to bid.", field="closes_at")
    if closes_at > pickup_at:
        raise DomainError("Bidding must close before the pickup time.", field="closes_at")
    if deliver_by <= pickup_at:
        raise DomainError("Delivery must be after pickup.", field="deliver_by")

    tender = Tender.objects.create(
        org=shipment.org,
        reference=next_number(org=shipment.org, doc_type="tender", prefix="TND"),
        shipment=shipment,
        vehicle_type=vehicle_type,
        pickup_at=pickup_at,
        deliver_by=deliver_by,
        closes_at=closes_at,
        target_rate=target_rate,
        currency=shipment.org.base_currency,
        notes=notes,
        created_by=actor,
    )
    tender.invited_carriers.set(carriers)
    audit.record(
        org=shipment.org,
        actor=actor,
        action="tender.created",
        entity=shipment,
        summary=f"Tender {tender.reference} opened to {len(carriers)} carrier(s), closes {closes_at:%d %b %H:%M} UTC",
    )
    return tender


def _lock_open(tender: Tender) -> Tender:
    close_expired(org=tender.org)
    tender = Tender.objects.select_for_update().get(pk=tender.pk)
    if tender.status != Tender.Status.OPEN:
        raise DomainError("Bidding on this tender has closed.", code="tender_closed")
    return tender


@transaction.atomic
def submit_bid(
    *, tender: Tender, carrier, actor, amount: Decimal, transit_hours: int, notes: str = ""
) -> Bid:
    """Place or revise a carrier's sealed bid while the tender is open."""
    tender = _lock_open(tender)
    if not tender.invited_carriers.filter(pk=carrier.pk).exists():
        raise DomainError("Your company wasn't invited to this tender.", code="not_invited")
    if amount <= 0:
        raise DomainError("Enter a positive rate.", field="amount")
    bid, created = Bid.objects.get_or_create(
        tender=tender,
        carrier=carrier,
        defaults={
            "org": tender.org,
            "amount": amount,
            "currency": tender.currency,
            "transit_hours": transit_hours,
            "notes": notes,
            "submitted_by": actor,
        },
    )
    if not created:
        bid.amount, bid.transit_hours, bid.notes = amount, transit_hours, notes
        bid.status, bid.submitted_by, bid.revision = Bid.Status.SUBMITTED, actor, bid.revision + 1
        bid.save()
    audit.record(
        org=tender.org,
        actor=actor,
        action="bid.submitted" if created else "bid.revised",
        entity=tender.shipment,
        summary=f"{carrier} {'bid' if created else 'revised bid to'} {amount} {tender.currency} on {tender.reference}",
    )
    return bid


@transaction.atomic
def withdraw_bid(*, tender: Tender, carrier, actor) -> Bid:
    tender = _lock_open(tender)
    bid = Bid.objects.filter(tender=tender, carrier=carrier, status=Bid.Status.SUBMITTED).first()
    if bid is None:
        raise DomainError("You have no active bid on this tender.")
    bid.status = Bid.Status.WITHDRAWN
    bid.save(update_fields=["status", "updated_at"])
    return bid


@transaction.atomic
def award(*, tender: Tender, bid: Bid, actor):
    """Pick the winner: book the carrier on the shipment and create the trip."""
    from apps.trips.services import create_from_award  # trips depends on tenders

    close_expired(org=tender.org)
    tender = Tender.objects.select_for_update().get(pk=tender.pk)
    if tender.status not in (Tender.Status.OPEN, Tender.Status.CLOSED):
        raise DomainError("This tender is no longer open to award.")
    if bid.tender_id != tender.pk or bid.status != Bid.Status.SUBMITTED:
        raise DomainError("Choose an active bid on this tender.", field="bid")

    tender.bids.exclude(pk=bid.pk).filter(status=Bid.Status.SUBMITTED).update(
        status=Bid.Status.LOST
    )
    bid.status = Bid.Status.WON
    bid.save(update_fields=["status", "updated_at"])
    tender.status, tender.awarded_bid = Tender.Status.AWARDED, bid
    tender.save(update_fields=["status", "awarded_bid", "updated_at"])

    shipment = tender.shipment
    shipment.carrier = bid.carrier
    shipment.save(update_fields=["carrier", "updated_at"])
    if shipment.status == ShipmentStatus.DRAFT:
        # Securing the truck is what confirms a road booking.
        from apps.shipments.services import change_status

        shipment = change_status(shipment=shipment, target=ShipmentStatus.BOOKED, actor=actor)
    trip = create_from_award(tender=tender, bid=bid, actor=actor)
    audit.record(
        org=tender.org,
        actor=actor,
        action="tender.awarded",
        entity=shipment,
        summary=f"Awarded {tender.reference} to {bid.carrier} at {bid.amount} {bid.currency}; trip {trip.reference} created",
    )
    return trip


@transaction.atomic
def cancel(*, tender: Tender, actor, reason: str) -> Tender:
    tender = Tender.objects.select_for_update().get(pk=tender.pk)
    if tender.status not in (Tender.Status.OPEN, Tender.Status.CLOSED):
        raise DomainError("Only open or closed tenders can be cancelled.")
    if not reason.strip():
        raise DomainError("Give a reason for cancelling.", field="reason")
    tender.status, tender.cancel_reason = Tender.Status.CANCELLED, reason.strip()
    tender.save(update_fields=["status", "cancel_reason", "updated_at"])
    tender.bids.filter(status=Bid.Status.SUBMITTED).update(status=Bid.Status.LOST)
    audit.record(
        org=tender.org,
        actor=actor,
        action="tender.cancelled",
        entity=tender.shipment,
        summary=f"Cancelled {tender.reference}: {reason.strip()}",
    )
    return tender
