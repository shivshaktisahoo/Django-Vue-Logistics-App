from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.tenders.models import Tender

from .conftest import PNG

pytestmark = pytest.mark.django_db
T = "/api/v1/tenders/"
TRIPS = "/api/v1/trips/"


def pod():
    return SimpleUploadedFile("pod.png", PNG, content_type="image/png")


def test_full_flow_tender_bid_award_dispatch_deliver(road):
    tender = road.ops.post(T, road.tender_body()).json()
    assert tender["reference"].startswith("TND-") and tender["status"] == "open"

    assert (
        road.dlt_client.post(
            f"{T}{tender['id']}/bid/", {"amount": "1750", "transit_hours": 30}
        ).status_code
        == 200
    )
    assert (
        road.ghl_client.post(
            f"{T}{tender['id']}/bid/", {"amount": "1690", "transit_hours": 36}
        ).status_code
        == 200
    )
    # Revising keeps one bid per carrier and bumps the revision.
    revised = road.dlt_client.post(
        f"{T}{tender['id']}/bid/", {"amount": "1650", "transit_hours": 30}
    ).json()
    assert revised["revision"] == 2

    # Sealed bidding: a carrier sees only its own bid and never the budget.
    carrier_view = road.dlt_client.get(f"{T}{tender['id']}/").json()
    assert (
        carrier_view["bids"] is None
        and carrier_view["target_rate"] is None
        and carrier_view["customer"] is None
    )
    assert carrier_view["my_bid"]["amount"] == "1650.00"
    ops_view = road.ops.get(f"{T}{tender['id']}/").json()
    assert [b["carrier_code"] for b in ops_view["bids"]] == ["DLT", "GHL"]  # cheapest first
    assert ops_view["target_rate"] == "1800.00" and ops_view["bid_count"] == 2

    winner = next(b for b in ops_view["bids"] if b["carrier_code"] == "DLT")
    trip_id = road.ops.post(f"{T}{tender['id']}/award/", {"bid": winner["id"]}).json()["trip_id"]
    assert (
        road.ops.get(f"/api/v1/shipments/{road.shipment['id']}/").json()["carrier"]["code"] == "DLT"
    )
    loser_view = road.ghl_client.get(f"{T}{tender['id']}/").json()
    assert (
        loser_view["my_bid"]["status"] == "lost" and loser_view["awarded_to"] == "Another carrier"
    )
    assert road.ghl_client.get(f"{TRIPS}{trip_id}/").status_code == 404  # not their trip

    trip = road.dlt_client.get(f"{TRIPS}{trip_id}/").json()
    assert trip["status"] == "planned" and trip["agreed_rate"] == "1650.00"
    assert [s["kind"] for s in trip["stops"]] == ["pickup", "delivery"]

    trip = road.dlt_client.post(
        f"{TRIPS}{trip_id}/assign/",
        {"vehicle": str(road.dlt_truck.id), "driver": str(road.dlt_driver.id)},
    ).json()
    assert trip["status"] == "dispatched" and trip["vehicle"]["plate_number"] == "DXB-1"

    pickup, delivery = trip["stops"]
    trip = road.dlt_client.post(f"{TRIPS}{trip_id}/stops/{pickup['id']}/complete/", {}).json()
    assert trip["status"] == "in_progress"
    assert (
        road.ops.get(f"/api/v1/shipments/{road.shipment['id']}/").json()["status"] == "in_transit"
    )

    road.dlt_client.post(f"{TRIPS}{trip_id}/stops/{delivery['id']}/arrive/")
    assert (
        road.ops.get(f"/api/v1/shipments/{road.shipment['id']}/").json()["status"]
        == "out_for_delivery"
    )

    no_pod = road.dlt_client.post(
        f"{TRIPS}{trip_id}/stops/{delivery['id']}/complete/", {"receiver_name": "K. Otaibi"}
    )
    assert no_pod.status_code == 400
    done = road.dlt_client.post(
        f"{TRIPS}{trip_id}/stops/{delivery['id']}/complete/",
        {"receiver_name": "K. Otaibi", "pod": pod()},
        format="multipart",
    ).json()
    assert done["status"] == "completed"
    shipment = road.ops.get(f"/api/v1/shipments/{road.shipment['id']}/").json()
    assert shipment["status"] == "delivered" and shipment["ata"]

    docs = road.customer_client.get("/api/v1/documents/", {"shipment": road.shipment["id"]}).json()
    assert [d["doc_type"] for d in docs] == ["pod"]
    events = road.customer_client.get(f"/api/v1/shipments/{road.shipment['id']}/events/").json()
    assert events[0]["code"] == "DLV" and events[0]["source"] == "carrier"


def test_uninvited_carrier_cannot_see_or_bid(road):
    tender = road.ops.post(T, road.tender_body(carriers=[str(road.ghl.id)])).json()
    assert road.dlt_client.get(f"{T}{tender['id']}/").status_code == 404
    assert (
        road.dlt_client.post(
            f"{T}{tender['id']}/bid/", {"amount": "1", "transit_hours": 1}
        ).status_code
        == 404
    )
    assert road.dlt_client.get(T).json()["count"] == 0


def test_bidding_closes_at_the_deadline(road):
    tender = road.ops.post(T, road.tender_body()).json()
    Tender.objects.filter(pk=tender["id"]).update(closes_at=timezone.now() - timedelta(minutes=1))
    resp = road.dlt_client.post(f"{T}{tender['id']}/bid/", {"amount": "1500", "transit_hours": 30})
    assert resp.status_code == 400 and "closed" in resp.json()["detail"]
    assert road.ops.get(f"{T}{tender['id']}/").json()["status"] == "closed"


def test_tender_rules(road):
    assert road.ops.post(T, road.tender_body(carriers=[str(road.maersk.id)])).status_code == 400
    assert (
        road.ops.post(T, road.tender_body(closes_at=timezone.now().isoformat())).status_code == 400
    )
    assert road.ops.post(T, road.tender_body()).status_code == 201
    assert road.ops.post(T, road.tender_body()).status_code == 400  # one live tender per shipment
    assert road.dlt_client.post(T, road.tender_body()).status_code == 403  # carriers don't tender


def _awarded_trip(road):
    tender = road.ops.post(T, road.tender_body()).json()
    bid = road.dlt_client.post(
        f"{T}{tender['id']}/bid/", {"amount": "1700", "transit_hours": 30}
    ).json()
    return road.ops.post(f"{T}{tender['id']}/award/", {"bid": bid["id"]}).json()["trip_id"]


def test_dispatch_checks_fleet_ownership_and_payload(road):
    trip_id = _awarded_trip(road)
    other_fleet = road.dlt_client.post(
        f"{TRIPS}{trip_id}/assign/",
        {"vehicle": str(road.ghl_truck.id), "driver": str(road.dlt_driver.id)},
    )
    assert other_fleet.status_code == 400 and "vehicle" in other_fleet.json()
    too_small = road.dlt_client.post(
        f"{TRIPS}{trip_id}/assign/",
        {"vehicle": str(road.dlt_van.id), "driver": str(road.dlt_driver.id)},
    )
    assert too_small.status_code == 400 and "12,000" in str(too_small.json())


def test_stops_run_in_order(road):
    trip_id = _awarded_trip(road)
    trip = road.dlt_client.post(
        f"{TRIPS}{trip_id}/assign/",
        {"vehicle": str(road.dlt_truck.id), "driver": str(road.dlt_driver.id)},
    ).json()
    delivery = trip["stops"][1]
    resp = road.dlt_client.post(
        f"{TRIPS}{trip_id}/stops/{delivery['id']}/complete/",
        {"receiver_name": "x", "pod": pod()},
        format="multipart",
    )
    assert resp.status_code == 400 and "stop 1" in resp.json()["detail"]


def test_ops_can_cancel_unstarted_trip_but_carrier_cannot(road):
    trip_id = _awarded_trip(road)
    assert road.dlt_client.post(f"{TRIPS}{trip_id}/cancel/", {"reason": "x"}).status_code == 403
    assert (
        road.ops.post(f"{TRIPS}{trip_id}/cancel/", {"reason": "Truck breakdown"}).json()["status"]
        == "cancelled"
    )
    assert road.ops.get(f"/api/v1/shipments/{road.shipment['id']}/").json()["carrier"] is None


def test_fleet_options_flag_fit_and_scope_to_own_carrier(road):
    trip_id = _awarded_trip(road)
    fleet = road.dlt_client.get(f"{TRIPS}{trip_id}/fleet/").json()
    plates = {v["plate_number"]: v["fits"] for v in fleet["vehicles"]}
    assert plates == {
        "DXB-1": True,
        "DXB-2": False,
    }  # the van can't take 12 t; GHL's truck isn't listed
    assert [d["name"] for d in fleet["drivers"]] == ["Imran"]
