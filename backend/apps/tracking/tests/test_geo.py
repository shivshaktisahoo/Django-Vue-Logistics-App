from datetime import UTC, datetime, timedelta

import pytest

from apps.tracking import geo

SHANGHAI, ROTTERDAM, JEBEL_ALI, DUBAI_AIR, AMSTERDAM_AIR = (
    (30.626, 122.065),
    (51.95, 4.14),
    (25.011, 55.061),
    (25.253, 55.366),
    (52.310, 4.768),
)


def test_haversine_known_distance():
    # Dubai → Amsterdam airports is ~5,160 km great-circle.
    assert 5100 < geo.haversine_km(DUBAI_AIR, AMSTERDAM_AIR) < 5250


def test_ocean_route_goes_via_malacca_and_suez_not_over_land():
    route = geo.sea_route(SHANGHAI, ROTTERDAM)
    names = {point: key for key, point in geo.SEA_NODES.items()}
    passed = [names[p] for p in route if p in names]
    for chokepoint in (
        "singapore_strait",
        "malacca_north",
        "bab_el_mandeb",
        "suez",
        "gibraltar",
        "dover",
    ):
        assert chokepoint in passed
    assert route[0] == SHANGHAI and route[-1] == ROTTERDAM
    # Real-world Shanghai–Rotterdam via Suez is ~19,500 km; a straight line is ~8,900.
    assert 18_500 < geo.route_length_km(route) < 21_000


def test_air_route_is_a_great_circle():
    route = geo.route_for("air", DUBAI_AIR, AMSTERDAM_AIR)
    assert len(route) == 33
    assert route[0] == pytest.approx(DUBAI_AIR, abs=1e-6)
    assert route[-1] == pytest.approx(AMSTERDAM_AIR, abs=1e-6)
    assert geo.route_length_km(route) == pytest.approx(
        geo.haversine_km(DUBAI_AIR, AMSTERDAM_AIR), rel=0.001
    )


def test_point_along_endpoints_and_midpoint():
    route = [(0.0, 0.0), (0.0, 10.0)]
    assert geo.point_along(route, 0)[0] == (0.0, 0.0)
    assert geo.point_along(route, 1)[0] == (0.0, 10.0)
    (lat, lng), heading = geo.point_along(route, 0.5)
    assert (lat, lng) == pytest.approx((0.0, 5.0))
    assert heading == pytest.approx(90)  # due east


NOW = datetime(2026, 9, 26, 12, tzinfo=UTC)


@pytest.mark.parametrize(
    ("status", "phase"),
    [
        ("booked", "at_origin"),
        ("picked_up", "at_origin"),
        ("at_customs", "at_destination"),
        ("delivered", "at_destination"),
    ],
)
def test_position_follows_lifecycle(status, phase):
    pos = geo.estimate_position(
        mode="road",
        status=status,
        route=[JEBEL_ALI, DUBAI_AIR],
        departed=NOW,
        eta=NOW + timedelta(days=1),
        now=NOW,
    )
    assert pos.phase == phase


def test_in_transit_position_interpolates_on_the_clock():
    route = [(0.0, 0.0), (0.0, 10.0)]
    pos = geo.estimate_position(
        mode="road",
        status="in_transit",
        route=route,
        departed=NOW - timedelta(hours=5),
        eta=NOW + timedelta(hours=15),
        now=NOW,
    )
    assert pos.progress == pytest.approx(0.25)
    assert pos.lng == pytest.approx(2.5, abs=0.01)


def test_overdue_cargo_is_held_short_of_destination():
    pos = geo.estimate_position(
        mode="road",
        status="in_transit",
        route=[(0.0, 0.0), (0.0, 10.0)],
        departed=NOW - timedelta(days=5),
        eta=NOW - timedelta(days=1),
        now=NOW,
    )
    assert pos.progress == 0.97


def test_drafts_have_no_position():
    assert (
        geo.estimate_position(
            mode="air", status="draft", route=[DUBAI_AIR], departed=None, eta=None, now=NOW
        )
        is None
    )
