"""Demo data for road procurement: tenders, sealed bids, awards and trips.

Tenders are created and awarded through the real services under the seed's frozen
clock, right after each road booking. Trip execution is then mirrored from the
shipment's recorded milestones, so a delivered shipment has a completed trip with a
signed POD, and an in-transit one has a truck on the road.
"""

from datetime import timedelta
from decimal import Decimal
from itertools import cycle

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.documents import services as documents
from apps.documents.models import ShipmentDocument
from apps.masterdata.models import Driver, Vehicle
from apps.organizations.permissions import Role
from apps.shipments import services as shipment_services
from apps.shipments.domain import ShipmentStatus as S
from apps.tenders import services as tenders
from apps.tenders.models import Bid, Tender
from apps.trips.models import Trip

RATE_PER_KM = {"DLT": Decimal("1.55"), "GHL": Decimal("1.62")}
LANE_KM = {
    ("AEJEA", "SARUH"): 1010,
    ("JAFZADC", "OMSOH"): 250,
    ("JAFZADC", "SAJED"): 1950,
    ("AEJEA", "AEAUH"): 110,
}
RECEIVERS = ["K. Al Otaibi", "S. Al Harthy", "M. Rahman", "A. Qasim", "R. Nair", "F. Saleh"]


def _frozen(at):
    from .seed import frozen_clock

    return frozen_clock(at)


def _quote(rng, carrier_code: str, lane: tuple[str, str]) -> Decimal:
    km = LANE_KM.get(lane, 500)
    base = Decimal(km) * RATE_PER_KM[carrier_code] + Decimal(250)
    return (base * Decimal(str(rng.uniform(0.94, 1.08)))).quantize(Decimal("10"))


def _vehicle_type(shipment) -> str:
    if shipment.is_temperature_controlled:
        return Vehicle.Type.REEFER
    return (
        Vehicle.Type.TRACTOR_TRAILER if shipment.service_type == "ftl" else Vehicle.Type.BOX_TRUCK
    )


def tender_and_award(*, shipment, booked_at, users, carriers, rng, now, award: bool = True):
    """Open a tender at booking time, collect two bids, award the lane's usual carrier."""
    ops, carrier_user = users[Role.OPS], users[Role.CARRIER]
    lane = (shipment.origin.code, shipment.destination.code)
    winner_code = shipment.carrier.code if shipment.carrier else "DLT"
    loser_code = "GHL" if winner_code == "DLT" else "DLT"
    opened = booked_at + timedelta(minutes=20)
    closes = opened + timedelta(hours=2)
    pickup = shipment.etd - timedelta(hours=3)
    if opened >= now or closes >= pickup:
        return None
    with _frozen(opened):
        tender = tenders.create_tender(
            shipment=shipment,
            actor=ops,
            carriers=[carriers["DLT"], carriers["GHL"]],
            vehicle_type=_vehicle_type(shipment),
            pickup_at=pickup,
            deliver_by=shipment.eta + timedelta(hours=12),
            closes_at=closes,
            target_rate=(_quote(rng, "DLT", lane) * Decimal("1.05")).quantize(Decimal("10")),
            notes="Tail-lift not required. Driver to carry Iqama/Emirates ID for port access.",
        )
    win_amount = _quote(rng, winner_code, lane)
    bids = {}
    for code, offset, amount in (
        (loser_code, timedelta(minutes=35), win_amount + Decimal(rng.randrange(40, 160))),
        (winner_code, timedelta(minutes=70), win_amount),
    ):
        at = opened + offset
        if at >= now:
            continue
        with _frozen(at):
            bids[code] = tenders.submit_bid(
                tender=tender,
                carrier=carriers[code],
                actor=carrier_user if code == "DLT" else None,
                amount=amount,
                transit_hours=int((shipment.eta - shipment.etd).total_seconds() // 3600)
                + rng.randrange(0, 6),
            )
    award_at = closes + timedelta(minutes=15)
    if award and winner_code in bids and award_at < now and award_at < pickup:
        with _frozen(award_at):
            tenders.award(tender=tender, bid=bids[winner_code], actor=ops)
    return tender


def simple_pdf(title: str, lines: list[str]) -> bytes:
    """A small, valid one-page PDF: enough to open in any viewer."""

    def esc(text: str) -> str:
        text = text.encode("latin-1", "replace").decode("latin-1")  # core PDF fonts are Latin-1
        return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    stream = (
        f"BT /F1 18 Tf 72 740 Td ({esc(title.upper())}) Tj /F1 11 Tf 0 -30 Td 16 TL "
        + " ".join(f"({esc(line)}) '" for line in lines)
        + " ET"
    )
    objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream",
    ]
    out, offsets = "%PDF-1.4\n", []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out.encode("latin-1")))
        out += f"{i} 0 obj\n{body}\nendobj\n"
    xref = len(out.encode("latin-1"))
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n" + "".join(
        f"{o:010d} 00000 n \n" for o in offsets
    )
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    return out.encode("latin-1")


def sync_trips(*, org, users, rng, now) -> None:
    """Mirror each trip's progress from its shipment's recorded milestones."""
    fleets = {}
    for trip in Trip.objects.filter(org=org).select_related("carrier").order_by("planned_start"):
        stops = list(trip.stops.select_related("shipment", "location"))
        pickup, delivery = stops[0], stops[-1]
        shipment = pickup.shipment
        shipment.refresh_from_db()
        if shipment.status == S.CANCELLED:
            trip.status = Trip.Status.CANCELLED
            trip.save(update_fields=["status"])
            continue
        events = {}
        for e in shipment.events.order_by("occurred_at"):
            events.setdefault(e.code, e.occurred_at)

        pickup_soon = trip.planned_start - now < timedelta(hours=36)
        if shipment.status != S.BOOKED or pickup_soon:
            if trip.carrier_id not in fleets:
                fleets[trip.carrier_id] = (
                    cycle(
                        list(
                            Vehicle.objects.filter(carrier=trip.carrier).exclude(vehicle_type="van")
                        )
                    ),
                    cycle(list(Driver.objects.filter(carrier=trip.carrier))),
                )
            vehicles, drivers = fleets[trip.carrier_id]
            vehicle = next(vehicles)
            if shipment.is_temperature_controlled:
                vehicle = (
                    Vehicle.objects.filter(carrier=trip.carrier, vehicle_type="reefer").first()
                    or vehicle
                )
            trip.vehicle, trip.driver, trip.status = vehicle, next(drivers), Trip.Status.DISPATCHED

        if "PUP" in events:
            pickup.arrived_at = events["PUP"] - timedelta(minutes=40)
            pickup.completed_at = events["PUP"]
            pickup.save(update_fields=["arrived_at", "completed_at"])
            trip.status, trip.started_at = Trip.Status.IN_PROGRESS, events["PUP"]
        if "OFD" in events:
            delivery.arrived_at = events["OFD"]
            delivery.save(update_fields=["arrived_at"])
        if "DLV" in events:
            receiver = rng.choice(RECEIVERS)
            delivery.completed_at, delivery.receiver_name = events["DLV"], receiver
            delivery.save(update_fields=["completed_at", "receiver_name"])
            trip.status, trip.completed_at = Trip.Status.COMPLETED, events["DLV"]
            pdf = simple_pdf(
                "Proof of delivery",
                [
                    f"Shipment: {shipment.reference}   Trip: {trip.reference}",
                    f"Carrier: {trip.carrier.name}   Vehicle: {trip.vehicle.plate_number if trip.vehicle else '-'}",
                    f"Delivered to: {shipment.consignee.name}, {delivery.location.name}",
                    f"Received by: {receiver}   at {events['DLV']:%d %b %Y %H:%M} UTC",
                    f"Packages: {shipment.total_packages}   Gross weight: {shipment.gross_weight_kg} kg",
                    "Goods received in good order and condition.",
                ],
            )
            with _frozen(events["DLV"]):
                documents.upload(
                    shipment=shipment,
                    actor=users[Role.CARRIER] if trip.carrier.code == "DLT" else None,
                    file=SimpleUploadedFile(f"POD-{shipment.reference}.pdf", pdf),
                    doc_type=ShipmentDocument.DocType.POD,
                    notes=f"Signed by {receiver}",
                    trip=trip,
                )
        trip.save()


def open_marketplace(*, org, users, carriers, locations, parties, rng, now) -> None:
    """Fresh tenders so the carrier persona has bidding to do and ops has one to award."""
    ops = users[Role.OPS]
    specs = [
        # (origin, dest, customer, shipper, consignee, commodity, created ago, closes after creation, bidders)
        ("AEJEA", "SARUH", "ALNOOR", "ALNOOR", "RRHUB", "Washing machines", 3, 26, ("GHL",)),
        ("JAFZADC", "OMSOH", "EAGRO", "EAGRO", "MUSCAT", "Frozen poultry", 2, 9, ("GHL", "DLT")),
        (
            "JAFZADC",
            "SAJED",
            "ALNOOR",
            "ALNOOR",
            "RRHUB",
            "Split air conditioners",
            30,
            26,
            ("DLT", "GHL"),
        ),
        ("AEJEA", "AEAUH", "BHARAT", "BHARAT", "ALNOOR", "Brake pads", 1, 32, ()),
    ]
    for origin, dest, customer, shipper, consignee, commodity, ago_h, window_h, bidders in specs:
        created = now - timedelta(hours=ago_h)
        frozen = "Frozen" in commodity
        qty = rng.randrange(16, 24)
        with _frozen(created):
            shipment = shipment_services.create_shipment(
                org=org,
                actor=ops,
                book=True,
                packages=[
                    {
                        "kind": "pallet",
                        "quantity": qty,
                        "description": commodity,
                        "weight_kg": Decimal(qty * rng.randrange(400, 700)),
                        "length_cm": Decimal(120),
                        "width_cm": Decimal(100),
                        "height_cm": Decimal(150),
                    }
                ],
                mode="road",
                service_type="ftl",
                incoterm="DAP",
                customer=parties[customer],
                shipper=parties[shipper],
                consignee=parties[consignee],
                origin=locations[origin],
                destination=locations[dest],
                etd=(created + timedelta(hours=window_h + 20)).replace(
                    minute=0, second=0, microsecond=0
                ),
                eta=(
                    created + timedelta(hours=window_h + 20 + (LANE_KM[(origin, dest)] // 60) + 8)
                ).replace(minute=0, second=0, microsecond=0),
                commodity=commodity,
                is_temperature_controlled=frozen,
                customer_reference=f"PO-{rng.randrange(10**5, 10**6)}",
            )
            tender = tenders.create_tender(
                shipment=shipment,
                actor=ops,
                carriers=[carriers["DLT"], carriers["GHL"]],
                vehicle_type=Vehicle.Type.REEFER if frozen else Vehicle.Type.TRACTOR_TRAILER,
                pickup_at=shipment.etd - timedelta(hours=3),
                deliver_by=shipment.eta + timedelta(hours=12),
                closes_at=created + timedelta(hours=window_h),
                target_rate=(_quote(rng, "DLT", (origin, dest)) * Decimal("1.04")).quantize(
                    Decimal("10")
                ),
                notes="Reefer set-point -18 °C, continuous temperature log required."
                if frozen
                else "",
            )
        for n, code in enumerate(bidders):
            at = min(created + timedelta(minutes=40 + 50 * n), now - timedelta(minutes=5))
            with _frozen(at):
                tenders.submit_bid(
                    tender=tender,
                    carrier=carriers[code],
                    actor=users[Role.CARRIER] if code == "DLT" else None,
                    amount=_quote(rng, code, (origin, dest)),
                    transit_hours=LANE_KM[(origin, dest)] // 60 + rng.randrange(4, 10),
                )
    tenders.close_expired(org=org, now=timezone.now())

    # Two jobs already won by Desert Line, so the carrier persona has a truck to run.
    _awarded_job(
        org=org,
        users=users,
        carriers=carriers,
        locations=locations,
        parties=parties,
        rng=rng,
        now=now,
        lane=("AEJEA", "SARUH"),
        customer="ALNOOR",
        consignee="RRHUB",
        commodity="Refrigerators",
        created_ago=timedelta(hours=20),
        pickup_in=timedelta(hours=4),
        plate="DXB-P-48214",
        driver="Joseph Mathew",
        start=False,
    )
    _awarded_job(
        org=org,
        users=users,
        carriers=carriers,
        locations=locations,
        parties=parties,
        rng=rng,
        now=now,
        lane=("JAFZADC", "OMSOH"),
        customer="EAGRO",
        consignee="MUSCAT",
        commodity="Dairy products (chilled)",
        created_ago=timedelta(hours=30),
        pickup_in=timedelta(hours=-3),
        plate="DXB-K-10977",
        driver="Imran Qureshi",
        start=True,
    )


def _awarded_job(
    *,
    org,
    users,
    carriers,
    locations,
    parties,
    rng,
    now,
    lane,
    customer,
    consignee,
    commodity,
    created_ago,
    pickup_in,
    plate,
    driver,
    start,
):
    from apps.trips import services as trips

    ops = users[Role.OPS]
    created = now - created_ago
    pickup = (now + pickup_in).replace(second=0, microsecond=0)
    chilled = "chilled" in commodity
    qty = rng.randrange(14, 22)
    with _frozen(created):
        shipment = shipment_services.create_shipment(
            org=org,
            actor=ops,
            book=True,
            packages=[
                {
                    "kind": "pallet",
                    "quantity": qty,
                    "description": commodity,
                    "weight_kg": Decimal(qty * rng.randrange(450, 650)),
                    "length_cm": Decimal(120),
                    "width_cm": Decimal(100),
                    "height_cm": Decimal(150),
                }
            ],
            mode="road",
            service_type="ftl",
            incoterm="DAP",
            customer=parties[customer],
            shipper=parties[customer],
            consignee=parties[consignee],
            origin=locations[lane[0]],
            destination=locations[lane[1]],
            etd=pickup + timedelta(hours=1),
            eta=pickup + timedelta(hours=LANE_KM[lane] // 60 + 3),
            commodity=commodity,
            is_temperature_controlled=chilled,
            customer_reference=f"PO-{rng.randrange(10**5, 10**6)}",
        )
        tender = tenders.create_tender(
            shipment=shipment,
            actor=ops,
            carriers=[carriers["DLT"], carriers["GHL"]],
            vehicle_type=Vehicle.Type.REEFER if chilled else Vehicle.Type.TRACTOR_TRAILER,
            pickup_at=pickup,
            deliver_by=pickup + timedelta(hours=LANE_KM[lane] // 60 + 12),
            closes_at=created + timedelta(hours=2),
            target_rate=(_quote(rng, "DLT", lane) * Decimal("1.05")).quantize(Decimal("10")),
        )
    bids = {}
    for n, code in enumerate(("GHL", "DLT")):
        with _frozen(created + timedelta(minutes=30 + 30 * n)):
            bids[code] = tenders.submit_bid(
                tender=tender,
                carrier=carriers[code],
                actor=users[Role.CARRIER] if code == "DLT" else None,
                amount=_quote(rng, code, lane) - (Decimal(60) if code == "DLT" else 0),
                transit_hours=LANE_KM[lane] // 60 + 4,
            )
    with _frozen(created + timedelta(hours=2, minutes=20)):
        trip = tenders.award(tender=tender, bid=bids["DLT"], actor=ops)
    with _frozen(created + timedelta(hours=3)):
        trip = trips.assign(
            trip=trip,
            actor=users[Role.CARRIER],
            vehicle=Vehicle.objects.get(org=org, plate_number=plate),
            driver=Driver.objects.get(org=org, name=driver),
        )
    if start:
        with _frozen(pickup):
            trips.complete(trip=trip, stop=trip.stops.get(sequence=1), actor=users[Role.CARRIER])


__all__ = ["Bid", "Tender", "open_marketplace", "sync_trips", "tender_and_award"]
