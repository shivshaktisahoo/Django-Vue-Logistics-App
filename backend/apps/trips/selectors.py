from django.db.models import Prefetch, QuerySet

from apps.organizations.permissions import Role

from .models import Trip, TripStop


def trips_for(*, membership) -> QuerySet[Trip]:
    qs = (
        Trip.objects.for_org(membership.org)
        .select_related("carrier", "vehicle", "driver", "tender")
        .prefetch_related(
            Prefetch(
                "stops",
                queryset=TripStop.objects.select_related(
                    "location", "shipment__consignee", "shipment__shipper"
                ),
            )
        )
    )
    if membership.role == Role.CARRIER:
        return qs.filter(carrier_id=membership.carrier_id) if membership.carrier_id else qs.none()
    return qs
