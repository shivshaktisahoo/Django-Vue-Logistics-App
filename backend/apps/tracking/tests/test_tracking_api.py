import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def moving(world, booked, client_for):
    client = client_for(world.ops, world.org)
    for target in ("picked_up", "in_transit"):
        assert (
            client.post(f"/api/v1/shipments/{booked['id']}/status/", {"target": target}).status_code
            == 200
        )
    return booked


def test_live_map_lists_moving_shipments_with_position_and_route(world, moving, client_for):
    rows = client_for(world.ops, world.org).get("/api/v1/tracking/live/").json()
    assert [r["id"] for r in rows] == [moving["id"]]
    row = rows[0]
    assert row["position"]["phase"] == "moving"
    assert len(row["route"]) > 5  # sea lane via waypoints, not a straight line
    assert row["distance_km"] > 8000


def test_live_map_excludes_booked_and_respects_customer_scope(world, booked, client_for):
    ops = client_for(world.ops, world.org)
    assert ops.get("/api/v1/tracking/live/").json() == []  # booked: not moving yet
    other = ops.post(
        "/api/v1/shipments/", world.payload(customer=str(world.globex.id), book=True)
    ).json()
    for s in (booked, other):
        ops.post(f"/api/v1/shipments/{s['id']}/status/", {"target": "picked_up"})
    ids = [
        r["id"] for r in client_for(world.customer, world.org).get("/api/v1/tracking/live/").json()
    ]
    assert ids == [booked["id"]]


def test_public_tracking_needs_no_login_and_hides_commercial_data(
    world, moving, api_client, client_for
):
    client_for(world.ops, world.org).post(
        f"/api/v1/shipments/{moving['id']}/events/",
        {
            "code": "NTE",
            "occurred_at": moving["created_at"],
            "description": "Internal: rate dispute",
            "is_public": False,
        },
    )
    resp = api_client.get(f"/api/v1/public/track/{moving['tracking_number'].lower()}/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "in_transit"
    assert body["forwarder"] == "Gulfstream"
    assert body["position"]["phase"] == "moving"
    text = str(body)
    for private in ("Acme", "Ningbo", "12000", "rate dispute", moving["reference"]):
        assert private not in text
    assert [e["code"] for e in body["events"]] == ["DEP", "PUP", "BKD"]


def test_public_tracking_unknown_or_draft_is_404(world, client_for, api_client):
    draft = client_for(world.ops, world.org).post("/api/v1/shipments/", world.payload()).json()
    assert api_client.get(f"/api/v1/public/track/{draft['tracking_number']}/").status_code == 404
    assert api_client.get("/api/v1/public/track/CPNOTREAL123/").status_code == 404
