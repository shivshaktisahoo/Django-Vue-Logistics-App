from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.audit.models import AuditEntry
from apps.masterdata.models import Location

pytestmark = pytest.mark.django_db
URL = "/api/v1/shipments/"


def status(client, shipment_id, target, **extra):
    return client.post(f"{URL}{shipment_id}/status/", {"target": target, **extra})


# ---------------------------------------------------------------- booking


def test_ops_books_shipment_with_reference_totals_and_milestone(booked):
    assert booked["reference"] == f"SHP-{timezone.now().year}-000001"
    assert booked["tracking_number"].startswith("CP") and len(booked["tracking_number"]) == 12
    assert booked["status"] == "booked"
    assert booked["total_packages"] == 1
    assert Decimal(booked["gross_weight_kg"]) == Decimal("12000")
    assert booked["allowed_transitions"] == ["picked_up", "on_hold", "cancelled"]


def test_references_are_sequential(world, client_for):
    client = client_for(world.ops, world.org)
    refs = [client.post(URL, world.payload()).data["reference"] for _ in range(3)]
    assert [r[-3:] for r in refs] == ["001", "002", "003"]


def test_booking_writes_event_and_audit(world, booked, client_for):
    events = client_for(world.ops, world.org).get(f"{URL}{booked['id']}/events/").data
    assert [e["code"] for e in events] == ["BKD"]
    actions = set(
        AuditEntry.objects.filter(entity_id=booked["id"]).values_list("action", flat=True)
    )
    assert actions == {"shipment.created", "shipment.status_changed"}


def test_invalid_container_check_digit_rejected(world, client_for):
    body = world.payload()
    body["packages"][0]["container_number"] = "CSQU3054384"
    resp = client_for(world.ops, world.org).post(URL, body)
    assert resp.status_code == 400
    assert "ISO 6346" in str(resp.data)


def test_fcl_needs_a_container(world, client_for):
    body = world.payload(packages=[{"kind": "pallet", "quantity": 10, "weight_kg": "5000"}])
    assert client_for(world.ops, world.org).post(URL, body).status_code == 400


def test_service_must_match_mode(world, client_for):
    resp = client_for(world.ops, world.org).post(URL, world.payload(service_type="ftl"))
    assert resp.status_code == 400
    assert "service_type" in resp.data


def test_eta_must_follow_etd(world, client_for):
    now = timezone.now()
    body = world.payload(etd=now.isoformat(), eta=(now - timedelta(days=1)).isoformat())
    assert client_for(world.ops, world.org).post(URL, body).status_code == 400


def test_cannot_use_another_orgs_location(world, make_org, client_for):
    other = make_org(name="Rival")
    foreign = Location.objects.create(
        org=other,
        code="NLRTM",
        name="Rotterdam",
        kind="seaport",
        country="NL",
        latitude=Decimal("51.9"),
        longitude=Decimal("4.1"),
    )
    resp = client_for(world.ops, world.org).post(URL, world.payload(destination=str(foreign.id)))
    assert resp.status_code == 400
    assert "destination" in resp.data


# ---------------------------------------------------------------- lifecycle


def test_full_lifecycle_sets_actual_times(world, booked, client_for):
    client = client_for(world.ops, world.org)
    for target in ["picked_up", "in_transit", "at_customs", "out_for_delivery", "delivered"]:
        resp = status(client, booked["id"], target)
        assert resp.status_code == 200, resp.data
    assert resp.data["status"] == "delivered"
    assert resp.data["atd"] and resp.data["ata"]
    assert resp.data["allowed_transitions"] == []
    codes = [e["code"] for e in client.get(f"{URL}{booked['id']}/events/").data]
    assert codes == ["DLV", "OFD", "CUS", "DEP", "PUP", "BKD"]


def test_illegal_transition_rejected(world, booked, client_for):
    resp = status(client_for(world.ops, world.org), booked["id"], "delivered")
    assert resp.status_code == 400
    assert "Can't move" in resp.data["detail"]


def test_hold_needs_reason_and_resume_restores_status(world, booked, client_for):
    client = client_for(world.ops, world.org)
    status(client, booked["id"], "picked_up")
    assert status(client, booked["id"], "on_hold").status_code == 400
    held = status(client, booked["id"], "on_hold", note="Missing invoice").data
    assert held["status"] == "on_hold" and held["allowed_transitions"] == ["resume"]
    resumed = status(client, booked["id"], "resume").data
    assert resumed["status"] == "picked_up"


def test_future_milestone_rejected(world, booked, client_for):
    future = (timezone.now() + timedelta(hours=2)).isoformat()
    resp = status(client_for(world.ops, world.org), booked["id"], "picked_up", occurred_at=future)
    assert resp.status_code == 400


def test_route_locked_after_pickup_but_eta_editable(world, booked, client_for):
    client = client_for(world.ops, world.org)
    status(client, booked["id"], "picked_up")
    assert client.patch(f"{URL}{booked['id']}/", {"commodity": "Changed"}).status_code == 400
    new_eta = (timezone.now() + timedelta(days=9)).isoformat()
    assert client.patch(f"{URL}{booked['id']}/", {"eta": new_eta}).status_code == 200


def test_manual_events_cannot_fake_status_milestones(world, booked, client_for):
    client = client_for(world.ops, world.org)
    now = timezone.now().isoformat()
    assert (
        client.post(f"{URL}{booked['id']}/events/", {"code": "DLV", "occurred_at": now}).status_code
        == 400
    )
    ok = client.post(f"{URL}{booked['id']}/events/", {"code": "GIN", "occurred_at": now})
    assert ok.status_code == 201


# ---------------------------------------------------------------- customer portal scope


def _customer_payload(world, **overrides):
    """Customers book with parties from their own address book."""
    from apps.masterdata.models import Party

    supplier = Party.objects.create(
        org=world.org, name="Acme Supplier", code="ACMESUP", country="CN", owner=world.acme
    )
    return world.payload(shipper=str(supplier.id), consignee=str(world.acme.id), **overrides)


def test_customer_booking_is_forced_to_own_account_as_draft(world, client_for):
    client = client_for(world.customer, world.org)
    body = _customer_payload(world, book=True)
    body.pop("customer")
    resp = client.post(URL, body)
    assert resp.status_code == 201, resp.data
    assert resp.data["customer"]["id"] == str(world.acme.id)
    assert resp.data["status"] == "draft"


def test_customer_cannot_reference_other_customers_or_their_parties(world, client_for):
    client = client_for(world.customer, world.org)
    resp = client.post(URL, _customer_payload(world, customer=str(world.globex.id)))
    assert resp.status_code == 400 and "customer" in resp.data
    resp = client.post(URL, world.payload(customer=str(world.acme.id)))  # ops' shipper, not theirs
    assert resp.status_code == 400 and "shipper" in resp.data


def test_customer_sees_only_own_shipments(world, booked, client_for):
    ops = client_for(world.ops, world.org)
    other = ops.post(URL, world.payload(customer=str(world.globex.id))).data
    client = client_for(world.customer, world.org)
    ids = [s["id"] for s in client.get(URL).data["results"]]
    assert ids == [booked["id"]]
    assert client.get(f"{URL}{other['id']}/").status_code == 404


def test_customer_cannot_move_confirmed_shipment(world, booked, client_for):
    client = client_for(world.customer, world.org)
    assert status(client, booked["id"], "cancelled", note="x").status_code == 403
    assert client.patch(f"{URL}{booked['id']}/", {"commodity": "x"}).status_code == 403


def test_customer_can_cancel_own_draft(world, client_for):
    client = client_for(world.customer, world.org)
    draft = client.post(URL, _customer_payload(world)).data
    assert draft["allowed_transitions"] == ["cancelled"]
    resp = status(client, draft["id"], "cancelled", note="Order changed")
    assert resp.status_code == 200 and resp.data["status"] == "cancelled"


def test_customer_does_not_see_internal_events(world, booked, client_for):
    ops = client_for(world.ops, world.org)
    now = timezone.now().isoformat()
    ops.post(
        f"{URL}{booked['id']}/events/", {"code": "NTE", "occurred_at": now, "is_public": False}
    )
    codes = [
        e["code"]
        for e in client_for(world.customer, world.org).get(f"{URL}{booked['id']}/events/").data
    ]
    assert codes == ["BKD"]


def test_carrier_role_has_no_shipment_list(world, client_for):
    assert client_for(world.carrier_user, world.org).get(URL).status_code == 403


def test_other_org_cannot_see_shipment(world, booked, make_org, client_for):
    rival = make_org(name="Rival")
    assert client_for(rival.owner, rival).get(f"{URL}{booked['id']}/").status_code == 404


# ---------------------------------------------------------------- list, filters, summary


def test_filters_search_and_summary(world, booked, client_for):
    client = client_for(world.ops, world.org)
    client.post(URL, world.payload(commodity="Ceramic tiles"))  # stays draft
    assert client.get(URL, {"status": "draft"}).data["count"] == 1
    assert client.get(URL, {"status": "draft,booked"}).data["count"] == 2
    assert client.get(URL, {"search": "ceramic"}).data["count"] == 1
    counts = client.get(f"{URL}summary/", {"status": "draft"}).data["counts"]
    assert counts == {"booked": 1, "draft": 1}  # status filter ignored for tab counts


def test_list_query_count_is_constant(world, client_for, django_assert_max_num_queries):
    client = client_for(world.ops, world.org)
    for _ in range(5):
        client.post(URL, world.payload())
    with django_assert_max_num_queries(6):
        assert client.get(URL).data["count"] == 5
