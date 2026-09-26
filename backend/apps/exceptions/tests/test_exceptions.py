from datetime import timedelta

import pytest
from django.utils import timezone

from apps.exceptions import detection
from apps.exceptions.models import ShipmentException as Exc
from apps.shipments.models import Shipment

pytestmark = pytest.mark.django_db
URL = "/api/v1/exceptions/"


def _move(client, shipment_id, *targets, **extra):
    for target in targets:
        resp = client.post(f"/api/v1/shipments/{shipment_id}/status/", {"target": target, **extra})
        assert resp.status_code == 200, resp.data


def _set_eta(shipment_id, delta):
    Shipment.objects.filter(pk=shipment_id).update(eta=timezone.now() + delta)


def test_overdue_shipment_raises_exception_and_delivery_auto_resolves_it(world, booked, client_for):
    client = client_for(world.ops, world.org)
    _move(client, booked["id"], "picked_up", "in_transit")
    _set_eta(booked["id"], timedelta(hours=-30))
    detection.scan(org=world.org)
    exc = Exc.objects.get(shipment_id=booked["id"], kind=Exc.Kind.ETA_OVERDUE)
    assert exc.status == "open" and exc.severity == "high"

    _move(client, booked["id"], "out_for_delivery", "delivered")
    exc.refresh_from_db()
    assert exc.status == "resolved" and exc.auto_resolved


def test_scan_is_idempotent_and_escalates_instead_of_duplicating(world, booked, client_for):
    client = client_for(world.ops, world.org)
    _move(client, booked["id"], "picked_up", "in_transit")
    _set_eta(booked["id"], timedelta(hours=-2))
    detection.scan(org=world.org)
    detection.scan(org=world.org)
    rows = Exc.objects.filter(shipment_id=booked["id"], kind=Exc.Kind.ETA_OVERDUE)
    assert rows.count() == 1 and rows[0].severity == "medium"

    client.post(f"{URL}{rows[0].id}/acknowledge/")
    _set_eta(booked["id"], timedelta(days=-4))
    detection.scan(org=world.org)
    row = rows.get()
    assert row.severity == "critical"
    assert row.status == "open"  # escalation re-opens an acknowledged exception


def test_at_risk_clears_when_cargo_reaches_customs(world, booked, client_for):
    client = client_for(world.ops, world.org)
    _move(client, booked["id"], "picked_up", "in_transit")
    _set_eta(booked["id"], timedelta(hours=10))
    detection.scan(org=world.org)
    assert Exc.objects.filter(kind=Exc.Kind.ETA_AT_RISK, status="open").count() == 1
    _move(client, booked["id"], "at_customs")
    assert Exc.objects.get(kind=Exc.Kind.ETA_AT_RISK).status == "resolved"


def test_long_hold_detected(world, booked, client_for):
    client = client_for(world.ops, world.org)
    two_days_ago = (timezone.now() - timedelta(days=2)).isoformat()
    _move(client, booked["id"], "picked_up")
    _move(client, booked["id"], "on_hold", note="Docs missing", occurred_at=two_days_ago)
    detection.scan(org=world.org)
    assert Exc.objects.get(kind=Exc.Kind.LONG_HOLD).severity == "medium"


def test_reported_delay_opens_exception_immediately(world, booked, client_for):
    client = client_for(world.ops, world.org)
    _move(client, booked["id"], "picked_up", "in_transit")
    client.post(
        f"/api/v1/shipments/{booked['id']}/events/",
        {
            "code": "DLY",
            "occurred_at": timezone.now().isoformat(),
            "description": "Port congestion +3 days",
        },
    )
    exc = Exc.objects.get(kind=Exc.Kind.DELAY_REPORTED)
    assert exc.detail == "Port congestion +3 days" and exc.status == "open"


def test_workflow_acknowledge_assign_resolve(world, booked, client_for):
    client = client_for(world.ops, world.org)
    _move(client, booked["id"], "picked_up", "in_transit")
    _set_eta(booked["id"], timedelta(hours=-5))
    detection.scan(org=world.org)
    exc_id = Exc.objects.get().id

    ack = client.post(f"{URL}{exc_id}/acknowledge/").json()
    assert ack["status"] == "acknowledged" and ack["assignee_name"]
    assert (
        client.post(f"{URL}{exc_id}/assign/", {"assignee": str(world.customer.id)}).status_code
        == 400
    )
    assert (
        client.post(f"{URL}{exc_id}/assign/", {"assignee": str(world.admin.id)}).status_code == 200
    )
    assert client.post(f"{URL}{exc_id}/resolve/", {"note": " "}).status_code == 400
    done = client.post(f"{URL}{exc_id}/resolve/", {"note": "Carrier confirmed new ETA"}).json()
    assert done["status"] == "resolved" and done["resolved_by_name"]
    summary = client.get(f"{URL}summary/").json()
    assert summary["open"] == 0 and summary["acknowledged"] == 0


def test_customer_sees_own_exceptions_read_only(world, booked, client_for):
    ops = client_for(world.ops, world.org)
    other = ops.post(
        "/api/v1/shipments/", world.payload(customer=str(world.globex.id), book=True)
    ).json()
    for s in (booked, other):
        _move(ops, s["id"], "picked_up", "in_transit")
        _set_eta(s["id"], timedelta(hours=-5))
    detection.scan(org=world.org)

    customer = client_for(world.customer, world.org)
    rows = customer.get(URL).json()["results"]
    assert [r["shipment"]["id"] for r in rows] == [booked["id"]]
    assert customer.post(f"{URL}{rows[0]['id']}/acknowledge/").status_code == 403
    assert customer.post(f"{URL}scan/").status_code == 403


def test_scan_endpoint(world, booked, client_for):
    client = client_for(world.ops, world.org)
    _move(client, booked["id"], "picked_up", "in_transit")
    _set_eta(booked["id"], timedelta(hours=-5))
    result = client.post(f"{URL}scan/").json()
    assert result["opened"] == 1 and result["scanned"] >= 1


def test_manual_resolve_suppresses_rescan_unless_it_gets_worse(world, booked, client_for):
    client = client_for(world.ops, world.org)
    _move(client, booked["id"], "picked_up", "in_transit")
    _set_eta(booked["id"], timedelta(hours=-5))
    detection.scan(org=world.org)
    exc = Exc.objects.get(kind=Exc.Kind.ETA_OVERDUE)
    client.post(f"{URL}{exc.id}/resolve/", {"note": "Customer agreed new ETA"})

    detection.scan(org=world.org)
    assert not Exc.objects.exclude(status="resolved").exists()  # same severity: stays quiet

    _set_eta(booked["id"], timedelta(days=-4))
    detection.scan(org=world.org)
    reopened = Exc.objects.exclude(status="resolved").get()
    assert reopened.severity == "critical"  # worse than what was handled: raise again
