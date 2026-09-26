"""Route geometry and live-position estimation. Pure Python, no database.

Ocean legs follow a small graph of real shipping-lane waypoints (Malacca, Bab-el-Mandeb,
Suez, Gibraltar, Hormuz…) instead of a straight line over land. Air legs follow the
great circle. Road legs are drawn direct; that's good enough at map zoom levels.

A vehicle's position is *computed* from departure time and ETA when it's read, rather
than stored as GPS pings. See ADR 0002: no background writes keep the database awake.
"""

import heapq
import math
from dataclasses import dataclass
from datetime import datetime

Point = tuple[float, float]  # (lat, lng)

EARTH_KM = 6371.0


def haversine_km(a: Point, b: Point) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return 2 * EARTH_KM * math.asin(math.sqrt(h))


def bearing(a: Point, b: Point) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    y = math.sin(lng2 - lng1) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lng2 - lng1)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def great_circle(a: Point, b: Point, steps: int = 32) -> list[Point]:
    """Points along the great circle from a to b (spherical linear interpolation)."""
    lat1, lng1, lat2, lng2 = map(math.radians, (*a, *b))
    d = 2 * math.asin(
        math.sqrt(
            math.sin((lat2 - lat1) / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
        )
    )
    if d == 0:
        return [a, b]
    out = []
    for i in range(steps + 1):
        f = i / steps
        A = math.sin((1 - f) * d) / math.sin(d)
        B = math.sin(f * d) / math.sin(d)
        x = A * math.cos(lat1) * math.cos(lng1) + B * math.cos(lat2) * math.cos(lng2)
        y = A * math.cos(lat1) * math.sin(lng1) + B * math.cos(lat2) * math.sin(lng2)
        z = A * math.sin(lat1) + B * math.sin(lat2)
        out.append((math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))))
    return out


# ---------------------------------------------------------------- sea lanes

SEA_NODES: dict[str, Point] = {
    "east_china_sea": (30.5, 123.5),
    "south_china_sea": (15.0, 115.0),
    "singapore_strait": (1.2, 104.2),
    "malacca_north": (6.0, 97.0),
    "sri_lanka": (5.8, 80.5),
    "off_mumbai": (18.5, 71.5),
    "arabian_sea": (15.0, 62.0),
    "gulf_of_oman": (24.8, 58.3),
    "hormuz": (26.4, 56.4),
    "gulf_of_aden": (12.3, 46.0),
    "bab_el_mandeb": (12.6, 43.3),
    "red_sea": (20.0, 38.5),
    "suez": (29.9, 32.55),
    "port_said": (31.6, 32.3),
    "central_med": (36.0, 15.0),
    "gibraltar": (35.95, -5.6),
    "off_portugal": (39.0, -10.5),
    "ushant": (48.5, -5.8),
    "dover": (51.0, 1.6),
    "north_sea": (53.3, 4.2),
    "elbe_mouth": (54.0, 8.3),
    "mid_atlantic": (40.0, -40.0),
    "off_new_york": (40.3, -73.3),
}

SEA_EDGES = [
    ("east_china_sea", "south_china_sea"),
    ("south_china_sea", "singapore_strait"),
    ("singapore_strait", "malacca_north"),
    ("malacca_north", "sri_lanka"),
    ("sri_lanka", "off_mumbai"),
    ("sri_lanka", "arabian_sea"),
    ("off_mumbai", "arabian_sea"),
    ("off_mumbai", "gulf_of_oman"),
    ("arabian_sea", "gulf_of_oman"),
    ("gulf_of_oman", "hormuz"),
    ("arabian_sea", "gulf_of_aden"),
    ("gulf_of_aden", "bab_el_mandeb"),
    ("bab_el_mandeb", "red_sea"),
    ("red_sea", "suez"),
    ("suez", "port_said"),
    ("port_said", "central_med"),
    ("central_med", "gibraltar"),
    ("gibraltar", "off_portugal"),
    ("off_portugal", "ushant"),
    ("ushant", "dover"),
    ("dover", "north_sea"),
    ("north_sea", "elbe_mouth"),
    ("off_portugal", "mid_atlantic"),
    ("mid_atlantic", "off_new_york"),
]


def _graph() -> dict[str, list[tuple[str, float]]]:
    g: dict[str, list[tuple[str, float]]] = {n: [] for n in SEA_NODES}
    for a, b in SEA_EDGES:
        d = haversine_km(SEA_NODES[a], SEA_NODES[b])
        g[a].append((b, d))
        g[b].append((a, d))
    return g


_SEA_GRAPH = _graph()


def _nearest_node(p: Point) -> str:
    return min(SEA_NODES, key=lambda n: haversine_km(p, SEA_NODES[n]))


def sea_route(a: Point, b: Point) -> list[Point]:
    """Shortest path through the lane graph, entered/exited at the nearest waypoints."""
    start, goal = _nearest_node(a), _nearest_node(b)
    dist, prev, queue = {start: 0.0}, {}, [(0.0, start)]
    while queue:
        d, node = heapq.heappop(queue)
        if node == goal:
            break
        if d > dist.get(node, math.inf):
            continue
        for nxt, w in _SEA_GRAPH[node]:
            nd = d + w
            if nd < dist.get(nxt, math.inf):
                dist[nxt], prev[nxt] = nd, node
                heapq.heappush(queue, (nd, nxt))
    path, node = [goal], goal
    while node != start:
        node = prev[node]
        path.append(node)
    waypoints = [SEA_NODES[n] for n in reversed(path)]
    points = [a, *waypoints, b]
    # Drop a waypoint that sends the ship backwards right next to the port.
    return [
        p
        for i, p in enumerate(points)
        if i in (0, len(points) - 1) or haversine_km(p, points[i - 1]) > 50
    ]


def route_for(mode: str, a: Point, b: Point) -> list[Point]:
    if mode == "ocean":
        return sea_route(a, b)
    if mode == "air":
        return great_circle(a, b)
    return [a, b]


def route_length_km(route: list[Point]) -> float:
    return sum(haversine_km(route[i], route[i + 1]) for i in range(len(route) - 1))


def point_along(route: list[Point], fraction: float) -> tuple[Point, float]:
    """The point `fraction` (0..1) of the way along the route, and the heading there."""
    fraction = min(max(fraction, 0.0), 1.0)
    legs = [haversine_km(route[i], route[i + 1]) for i in range(len(route) - 1)]
    target = sum(legs) * fraction
    for i, leg in enumerate(legs):
        if target <= leg or i == len(legs) - 1:
            f = 0 if leg == 0 else min(target / leg, 1.0)
            a, b = route[i], route[i + 1]
            # Linear interpolation inside one short leg is visually indistinguishable.
            point = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            return point, bearing(a, b)
        target -= leg
    return route[-1], 0.0


@dataclass(frozen=True)
class Position:
    lat: float
    lng: float
    heading: float
    progress: float  # 0..1 along the route
    phase: str  # at_origin | moving | at_destination


def estimate_position(
    *,
    mode: str,
    status: str,
    route: list[Point],
    departed: datetime | None,
    eta: datetime | None,
    now: datetime,
) -> Position | None:
    """Where the cargo most plausibly is right now, from its lifecycle status and schedule."""
    if status in ("draft", "cancelled") or not route:
        return None
    if status in ("booked", "picked_up") or departed is None:
        return Position(*route[0], heading=0.0, progress=0.0, phase="at_origin")
    if status in ("at_customs", "out_for_delivery", "delivered"):
        return Position(*route[-1], heading=0.0, progress=1.0, phase="at_destination")
    # In transit (or on hold while moving): interpolate on the clock. If the ETA has
    # passed without arrival, hold just short of the destination instead of pretending.
    if eta and eta > departed:
        fraction = (now - departed).total_seconds() / (eta - departed).total_seconds()
    else:
        fraction = 0.5
    fraction = min(max(fraction, 0.02), 0.97)
    (lat, lng), heading = point_along(route, fraction)
    return Position(lat, lng, heading, fraction, "moving")
