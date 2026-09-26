from functools import lru_cache

from django.utils import timezone

from apps.shipments.domain import eta_health
from apps.shipments.models import Shipment

from . import geo


@lru_cache(maxsize=512)
def _route(mode: str, a: geo.Point, b: geo.Point) -> tuple[geo.Point, ...]:
    return tuple(geo.route_for(mode, a, b))


def route_for_shipment(shipment: Shipment) -> list[geo.Point]:
    a = (float(shipment.origin.latitude), float(shipment.origin.longitude))
    b = (float(shipment.destination.latitude), float(shipment.destination.longitude))
    return list(_route(shipment.mode, a, b))


def live_view(shipment: Shipment, *, now=None, include_route: bool = True) -> dict:
    """Map-ready snapshot of a shipment: estimated position, progress, ETA health."""
    now = now or timezone.now()
    route = route_for_shipment(shipment)
    departed = shipment.atd or (shipment.etd if shipment.status == "in_transit" else None)
    pos = geo.estimate_position(
        mode=shipment.mode,
        status=shipment.status,
        route=route,
        departed=departed,
        eta=shipment.eta,
        now=now,
    )
    data = {
        "position": None
        if pos is None
        else {
            "lat": round(pos.lat, 4),
            "lng": round(pos.lng, 4),
            "heading": round(pos.heading),
            "progress": round(pos.progress, 3),
            "phase": pos.phase,
        },
        "eta_health": eta_health(shipment.status, shipment.eta, now),
        "distance_km": round(geo.route_length_km(route)),
    }
    if include_route:
        data["route"] = [[round(lat, 4), round(lng, 4)] for lat, lng in route]
    return data
