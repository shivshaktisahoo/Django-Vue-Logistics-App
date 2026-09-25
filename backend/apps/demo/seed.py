"""Builds the public demo workspace: one forwarder org, a user per role, master data
and ~40 shipments spread across every lifecycle stage.

Idempotent. `reset=True` deletes the demo org (cascading to all its data) and
rebuilds it, so visitors can create and edit freely and the nightly reset brings
the showcase back to a clean, realistic state.

Shipments are created through the real service layer under a frozen clock, so every
reference number, milestone, audit entry and timestamp is exactly what the app would
have produced had those events happened live.
"""

import random
from contextlib import contextmanager
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.services import demo_email
from apps.masterdata.models import Carrier, Driver, Location, Party, Vehicle
from apps.organizations.models import Membership, Organization
from apps.organizations.permissions import Role
from apps.shipments import services as shipment_services
from apps.shipments.domain import EventCode, ShipmentStatus, container_check_digit
from apps.shipments.models import Package, Shipment

from . import data

DEMO_ORG_NAME = "Gulfstream Freight Forwarders"
SHIPMENT_COUNT = 40

DEMO_PEOPLE = {
    Role.ADMIN: ("Aisha Rahman", "Operations Director"),
    Role.OPS: ("Rohan Mehta", "Ops Coordinator"),
    Role.CUSTOMER: ("Laura Chen", "Logistics Manager, Nordic Home Retail"),
    Role.CARRIER: ("Omar Haddad", "Dispatch Lead, Desert Line Transport"),
}

S = ShipmentStatus


@contextmanager
def frozen_clock(at: datetime):
    with patch("django.utils.timezone.now", return_value=at):
        yield


def _demo_user(role: str) -> User:
    name, title = DEMO_PEOPLE[role]
    user, _ = User.objects.get_or_create(
        email=demo_email(role), defaults={"full_name": name, "job_title": title, "is_demo": True}
    )
    user.full_name, user.job_title, user.is_demo = name, title, True
    user.set_password(settings.DEMO_PASSWORD)
    user.save()
    return user


@transaction.atomic
def seed_demo(*, reset: bool = False) -> Organization:
    if reset:
        for old in Organization.objects.filter(is_demo=True):
            # Shipments PROTECT their parties/locations, so they go first.
            Shipment.objects.filter(org=old).delete()
            old.delete()

    users = {role: _demo_user(role) for role in DEMO_PEOPLE}
    org = Organization.objects.filter(is_demo=True).first()
    if org is None:
        org = Organization.objects.create(
            is_demo=True,
            name=DEMO_ORG_NAME,
            legal_name="Gulfstream Freight Forwarders LLC",
            country="AE",
            base_currency="USD",
            timezone="Asia/Dubai",
            email="ops@gulfstream.example",
            phone="+971 4 555 0100",
            address="Jebel Ali Free Zone, Dubai, UAE",
            owner=users[Role.ADMIN],
        )
        _seed_workspace(org, users)
    return org


def _seed_workspace(org: Organization, users: dict[str, User]) -> None:
    rng = random.Random(20260925)
    locations = _seed_locations(org)
    carriers = _seed_carriers(org)
    parties = _seed_parties(org)

    scopes = {
        Role.CUSTOMER: {"party": parties["NORDIC"]},
        Role.CARRIER: {"carrier": carriers["DLT"]},
    }
    for role, user in users.items():
        Membership.objects.update_or_create(
            user=user, org=org, defaults={"role": role, "is_active": True, **scopes.get(role, {})}
        )

    _seed_shipments(org, users, rng, locations, carriers, parties)


def _seed_locations(org) -> dict[str, Location]:
    return {
        code: Location.objects.create(
            org=org,
            code=code,
            name=name,
            kind=kind,
            city=city,
            country=country,
            latitude=Decimal(str(lat)),
            longitude=Decimal(str(lng)),
            timezone=tz,
        )
        for code, name, kind, city, country, lat, lng, tz in data.LOCATIONS
    }


def _seed_carriers(org) -> dict[str, Carrier]:
    carriers = {
        code: Carrier.objects.create(
            org=org,
            name=name,
            code=code,
            mode=mode,
            country=country,
            email=f"bookings@{code.lower()}.example",
        )
        for name, code, mode, country in data.CARRIERS
    }
    for code, rows in data.VEHICLES.items():
        for plate, vtype, capacity in rows:
            Vehicle.objects.create(
                org=org,
                carrier=carriers[code],
                plate_number=plate,
                vehicle_type=vtype,
                capacity_kg=capacity,
            )
    for code, rows in data.DRIVERS.items():
        for name, phone, license_no in rows:
            Driver.objects.create(
                org=org, carrier=carriers[code], name=name, phone=phone, license_number=license_no
            )
    return carriers


def _seed_parties(org) -> dict[str, Party]:
    parties = {}
    for name, code, is_cust, is_ship, is_cons, city, country, contact, email in data.PARTIES:
        parties[code] = Party.objects.create(
            org=org,
            name=name,
            code=code,
            is_customer=is_cust,
            is_shipper=is_ship,
            is_consignee=is_cons,
            city=city,
            country=country,
            contact_name=contact,
            email=email,
        )
    for name, code, owner, city, country in data.ADDRESS_BOOK:
        parties[code] = Party.objects.create(
            org=org,
            name=name,
            code=code,
            is_consignee=True,
            owner=parties[owner],
            city=city,
            country=country,
        )
    return parties


# ---------------------------------------------------------------- shipments


def _container_number(rng, carrier_code: str) -> str:
    prefix = data.CONTAINER_OWNER[carrier_code] + f"{rng.randrange(10**6):06d}"
    return prefix + str(container_check_digit(prefix))


def _packages(rng, lane) -> list[dict]:
    mode, service, carrier, commodity = lane[2], lane[3], lane[4], lane[9]
    if service == "fcl":
        heavy = "machining" in commodity.lower() or "brake" in commodity.lower()
        return [
            {
                "kind": Package.Kind.CONTAINER,
                "container_type": "20GP" if heavy else rng.choice(["40HC", "40HC", "40GP"]),
                "container_number": _container_number(rng, carrier),
                "seal_number": f"SL{rng.randrange(10**7):07d}",
                "quantity": 1,
                "description": commodity,
                "weight_kg": Decimal(
                    rng.randrange(14000, 24000) if heavy else rng.randrange(7000, 16000)
                ),
            }
            for _ in range(rng.choice([1, 1, 2, 3]))
        ]
    if mode == "air":
        qty = rng.randrange(8, 60)
        return [
            {
                "kind": Package.Kind.CARTON,
                "quantity": qty,
                "description": commodity,
                "weight_kg": Decimal(qty * rng.randrange(6, 16)),
                "length_cm": Decimal(rng.choice([50, 60, 80])),
                "width_cm": Decimal(40),
                "height_cm": Decimal(rng.choice([30, 40, 50])),
            }
        ]
    qty = rng.randrange(18, 26) if service == "ftl" else rng.randrange(3, 12)
    return [
        {
            "kind": Package.Kind.PALLET,
            "quantity": qty,
            "description": commodity,
            "weight_kg": Decimal(qty * rng.randrange(300, 800)),
            "length_cm": Decimal(120),
            "width_cm": Decimal(100),
            "height_cm": Decimal(rng.choice([110, 140, 160])),
        }
    ]


def _references(rng, lane) -> dict:
    mode, carrier = lane[2], lane[4]
    if mode == "ocean":
        vessels = {"MAEU": "MAERSK EDINBURGH", "MSCU": "MSC ISABELLA", "HLCU": "BERLIN EXPRESS"}
        return {
            "house_bill": f"GSFF{rng.randrange(10**7):07d}",
            "master_bill": f"{carrier}{rng.randrange(10**9):09d}",
            "voyage_number": f"{vessels[carrier]} / {rng.randrange(400, 499)}{rng.choice('EW')}",
        }
    if mode == "air":
        prefix = {"EK": "176", "QR": "157"}[carrier]
        serial = rng.randrange(10**7)
        return {
            "house_bill": f"GSF{rng.randrange(10**6):06d}",
            "master_bill": f"{prefix}-{serial:07d}{serial % 7}",  # MAWB mod-7 check digit
            "voyage_number": f"{carrier}{rng.randrange(9000, 9999)}",
        }
    return {"house_bill": f"CMR-{rng.randrange(10**6):06d}"}


def _country(location_code: str) -> str:
    return "AE" if location_code == "JAFZADC" else location_code[:2]


def _plan(rng, lane, etd: datetime, eta: datetime, delay: timedelta) -> list[tuple]:
    """Chronological (kind, value, offset-time, note) steps for a shipment's life."""
    mode, origin, dest = lane[2], lane[0], lane[1]
    cross_border = _country(origin) != _country(dest)
    arrive = eta + delay
    steps = [("status", S.PICKED_UP, etd - timedelta(hours=18 if mode != "road" else 3), "")]
    if mode == "ocean":
        steps += [
            (
                "event",
                EventCode.GATE_IN,
                etd - timedelta(hours=12),
                "Full container gated in at terminal",
            ),
            ("event", EventCode.LOADED, etd - timedelta(hours=4), "Loaded on board"),
        ]
    steps.append(("status", S.IN_TRANSIT, etd, ""))
    if delay:
        steps.append(
            (
                "event",
                EventCode.DELAYED,
                etd + (eta - etd) * 0.6,
                rng.choice(
                    [
                        "Port congestion at transhipment hub; revised ETA +{d} days",
                        "Vessel omitted port call; cargo rolled to next sailing (+{d} days)",
                        "Weather delay reported by carrier (+{d} days)",
                    ]
                ).format(d=max(1, delay.days)),
            )
        )
    steps.append(("event", EventCode.ARRIVED, arrive, ""))
    if mode == "ocean":
        steps.append(
            ("event", EventCode.DISCHARGED, arrive + timedelta(hours=8), "Container discharged")
        )
    ready = arrive + timedelta(hours=2)
    if cross_border or mode != "road":
        cleared = arrive + timedelta(hours=rng.randrange(20, 72))
        steps += [
            ("status", S.AT_CUSTOMS, arrive + timedelta(hours=10), "Import declaration lodged"),
            ("event", EventCode.CUSTOMS_CLEARED, cleared, "Customs released"),
        ]
        ready = cleared + timedelta(hours=4)
    out = ready + timedelta(hours=rng.randrange(6, 30) if mode != "road" else 0)
    steps += [
        ("status", S.OUT_FOR_DELIVERY, out, ""),
        (
            "status",
            S.DELIVERED,
            out + timedelta(hours=rng.randrange(4, 20)),
            "Delivered, POD signed",
        ),
    ]
    return steps


def _seed_shipments(org, users, rng, locations, carriers, parties) -> None:
    now = timezone.now()
    ops, customer_user = users[Role.OPS], users[Role.CUSTOMER]

    # Skewed towards recent weeks so every lifecycle stage is populated "right now".
    specs = []
    for i in range(SHIPMENT_COUNT):
        lane = data.LANES[i % len(data.LANES)]
        age = timedelta(days=0.3 + 50 * rng.random() ** 1.5, minutes=rng.randrange(600))
        specs.append((now - age, i, lane, False))
    # A few bookings requested through the customer portal, awaiting ops confirmation.
    nordic_lanes = [lane for lane in data.LANES if lane[6] == "NORDIC"]
    for n in range(3):
        age = timedelta(hours=rng.randrange(3, 60))
        specs.append((now - age, SHIPMENT_COUNT + n, nordic_lanes[n % len(nordic_lanes)], True))
    specs.sort(key=lambda s: s[0])

    for created, i, lane, is_portal_draft in specs:
        origin, dest, mode, service, carrier, transit = lane[:6]
        customer, shipper, consignee, commodity, hs_code, incoterm = lane[6:]

        lead = timedelta(days=rng.uniform(1, 3) if mode == "air" else rng.uniform(2, 6))
        etd = (created + lead).replace(minute=0, second=0, microsecond=0)
        eta = etd + timedelta(days=transit, hours=rng.randrange(-6, 12) if mode != "air" else 6)
        delay = timedelta(days=rng.choice([2, 3, 4])) if rng.random() < 0.22 else timedelta()

        with frozen_clock(created):
            shipment = shipment_services.create_shipment(
                org=org,
                actor=customer_user if is_portal_draft else ops,
                packages=_packages(rng, lane),
                mode=mode,
                service_type=service,
                incoterm=incoterm,
                customer=parties[customer],
                shipper=parties[shipper],
                consignee=parties[consignee],
                origin=locations[origin],
                destination=locations[dest],
                carrier=carriers[carrier],
                etd=etd,
                eta=eta,
                commodity=commodity,
                hs_code=hs_code,
                declared_value=Decimal(rng.randrange(8, 400) * 1000),
                currency="USD",
                customer_reference=f"PO-{rng.randrange(10**5, 10**6)}",
                is_hazardous="Smartphone" in commodity,  # lithium batteries, UN3481
                is_temperature_controlled=any(w in commodity for w in ("chilled", "Frozen")),
                **_references(rng, lane),
            )
        if is_portal_draft:
            continue

        shipment = _apply(
            shipment, ops, S.BOOKED, created + timedelta(hours=rng.uniform(1, 5)), None, "", now
        )
        if i % 17 == 3:
            _apply(
                shipment,
                ops,
                S.CANCELLED,
                created + timedelta(hours=20),
                None,
                "Customer postponed the purchase order",
                now,
            )
            continue

        for kind, value, at, note in _plan(rng, lane, etd, eta, delay):
            if at > now - timedelta(minutes=30):
                break
            location = (
                locations[origin]
                if value in (EventCode.GATE_IN, EventCode.LOADED)
                else (
                    locations[dest]
                    if value in (EventCode.ARRIVED, EventCode.DISCHARGED, EventCode.CUSTOMS_CLEARED)
                    else None
                )
            )
            if kind == "status":
                shipment = _apply(shipment, ops, value, at, location, note, now)
            else:
                with frozen_clock(at):
                    shipment_services.add_event(
                        shipment=shipment,
                        actor=ops,
                        code=value,
                        occurred_at=at,
                        location=location,
                        description=note,
                    )
            if i % 13 == 5 and value == S.IN_TRANSIT:
                hold_at = at + timedelta(hours=10)
                if hold_at < now:
                    _apply(
                        shipment,
                        ops,
                        S.ON_HOLD,
                        hold_at,
                        None,
                        "Awaiting corrected commercial invoice from shipper",
                        now,
                    )
                break


def _apply(shipment: Shipment, actor, target, at, location, note, now) -> Shipment:
    at = min(at, now - timedelta(minutes=1))
    with frozen_clock(at):
        return shipment_services.change_status(
            shipment=shipment,
            target=target,
            actor=actor,
            occurred_at=at,
            location=location,
            note=note,
        )
