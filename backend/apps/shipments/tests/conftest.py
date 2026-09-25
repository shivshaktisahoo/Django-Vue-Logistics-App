from decimal import Decimal

import pytest

from apps.masterdata.models import Carrier, Location, Party
from apps.organizations.permissions import Role


class World:
    """One forwarder with enough master data to book shipments, plus a user per role."""

    def __init__(self, org, members, make_member):
        self.org = org
        self.admin = org.owner
        mk = lambda **kw: Party.objects.create(org=org, country="AE", **kw)  # noqa: E731
        self.acme = mk(name="Acme Retail", code="ACME", is_customer=True)
        self.globex = mk(name="Globex Trading", code="GLOBEX", is_customer=True)
        self.shipper = mk(name="Ningbo Mfg", code="NINGBO", is_shipper=True)
        self.consignee = mk(name="Acme DC", code="ACMEDC", is_consignee=True)
        self.jea = Location.objects.create(
            org=org,
            code="AEJEA",
            name="Jebel Ali",
            kind="seaport",
            country="AE",
            latitude=Decimal("25.0"),
            longitude=Decimal("55.0"),
        )
        self.sha = Location.objects.create(
            org=org,
            code="CNSHA",
            name="Shanghai",
            kind="seaport",
            country="CN",
            latitude=Decimal("30.6"),
            longitude=Decimal("122.0"),
        )
        self.maersk = Carrier.objects.create(org=org, name="Maersk", code="MAEU", mode="ocean")
        self.ops = make_member(org, Role.OPS).user
        customer = make_member(org, Role.CUSTOMER)
        customer.party = self.acme
        customer.save()
        self.customer = customer.user
        self.carrier_user = make_member(org, Role.CARRIER).user

    def payload(self, **overrides):
        body = {
            "mode": "ocean",
            "service_type": "fcl",
            "incoterm": "FOB",
            "customer": str(self.acme.id),
            "shipper": str(self.shipper.id),
            "consignee": str(self.consignee.id),
            "origin": str(self.sha.id),
            "destination": str(self.jea.id),
            "carrier": str(self.maersk.id),
            "commodity": "Furniture",
            "packages": [
                {
                    "kind": "container",
                    "container_type": "40HC",
                    "container_number": "CSQU3054383",
                    "quantity": 1,
                    "weight_kg": "12000",
                }
            ],
        }
        body.update(overrides)
        return body


@pytest.fixture
def world(make_org, make_member):
    return World(make_org(name="Gulfstream"), None, make_member)


@pytest.fixture
def booked(world, client_for):
    """A booked shipment for Acme, created by ops."""
    resp = client_for(world.ops, world.org).post("/api/v1/shipments/", world.payload(book=True))
    assert resp.status_code == 201, resp.data
    return resp.data
