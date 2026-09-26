from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.masterdata.models import Carrier, Driver, Location, Party, Vehicle
from apps.organizations.permissions import Role

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64  # smallest thing that sniffs as PNG


class RoadWorld:
    """A forwarder with two haulage partners, their fleets, and a booked FTL load."""

    def __init__(self, org, make_member, client_for):
        self.org = org
        party = lambda **kw: Party.objects.create(org=org, **{"country": "AE", **kw})  # noqa: E731
        self.customer = party(name="Acme Retail", code="ACME", is_customer=True)
        self.shipper = party(name="Acme DC", code="ACMEDC", is_shipper=True)
        self.consignee = party(
            name="Riyadh Store", code="RUHSTORE", is_consignee=True, country="SA"
        )

        def loc(code, **kw):
            return Location.objects.create(
                org=org, code=code, name=code, latitude=Decimal("25"), longitude=Decimal("55"), **kw
            )

        self.jea = loc("AEJEA", kind="seaport", country="AE")
        self.ruh = loc("SARUH", kind="inland", country="SA")
        self.dlt = Carrier.objects.create(org=org, name="Desert Line", code="DLT", mode="road")
        self.ghl = Carrier.objects.create(org=org, name="Gulf Hauliers", code="GHL", mode="road")
        self.maersk = Carrier.objects.create(org=org, name="Maersk", code="MAEU", mode="ocean")
        self.dlt_truck = Vehicle.objects.create(
            org=org,
            carrier=self.dlt,
            plate_number="DXB-1",
            vehicle_type="tractor_trailer",
            capacity_kg=26000,
        )
        self.dlt_van = Vehicle.objects.create(
            org=org, carrier=self.dlt, plate_number="DXB-2", vehicle_type="van", capacity_kg=1500
        )
        self.ghl_truck = Vehicle.objects.create(
            org=org,
            carrier=self.ghl,
            plate_number="SHJ-1",
            vehicle_type="tractor_trailer",
            capacity_kg=25000,
        )
        self.dlt_driver = Driver.objects.create(
            org=org, carrier=self.dlt, name="Imran", phone="1", license_number="L1"
        )
        self.ghl_driver = Driver.objects.create(
            org=org, carrier=self.ghl, name="Sunil", phone="2", license_number="L2"
        )

        self.ops = client_for(make_member(org, Role.OPS).user, org)
        self.dlt_member = make_member(org, Role.CARRIER)
        self.dlt_member.carrier = self.dlt
        self.dlt_member.save()
        self.dlt_client = client_for(self.dlt_member.user, org)
        ghl_member = make_member(org, Role.CARRIER)
        ghl_member.carrier = self.ghl
        ghl_member.save()
        self.ghl_client = client_for(ghl_member.user, org)
        cust = make_member(org, Role.CUSTOMER)
        cust.party = self.customer
        cust.save()
        self.customer_client = client_for(cust.user, org)

        resp = self.ops.post(
            "/api/v1/shipments/",
            {
                "mode": "road",
                "service_type": "ftl",
                "customer": str(self.customer.id),
                "shipper": str(self.shipper.id),
                "consignee": str(self.consignee.id),
                "origin": str(self.jea.id),
                "destination": str(self.ruh.id),
                "commodity": "Appliances",
                "book": True,
                "packages": [
                    {
                        "kind": "pallet",
                        "quantity": 20,
                        "weight_kg": "12000",
                        "length_cm": "120",
                        "width_cm": "100",
                        "height_cm": "150",
                    }
                ],
            },
        )
        assert resp.status_code == 201, resp.data
        self.shipment = resp.data

    def tender_body(self, **over):
        now = timezone.now()
        body = {
            "shipment": self.shipment["id"],
            "carriers": [str(self.dlt.id), str(self.ghl.id)],
            "vehicle_type": "tractor_trailer",
            "closes_at": (now + timedelta(hours=1)).isoformat(),
            "pickup_at": (now + timedelta(hours=3)).isoformat(),
            "deliver_by": (now + timedelta(days=2)).isoformat(),
            "target_rate": "1800",
        }
        body.update(over)
        return body


@pytest.fixture
def road(make_org, make_member, client_for):
    return RoadWorld(make_org(name="Gulfstream"), make_member, client_for)
