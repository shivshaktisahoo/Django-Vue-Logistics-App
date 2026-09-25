from django.db.models import Count, QuerySet

from apps.organizations.permissions import Role

from .models import Shipment, TrackingEvent


def shipments_for(*, membership) -> QuerySet[Shipment]:
    """Every shipment query starts here: tenant filter + row-level scope per role."""
    qs = Shipment.objects.for_org(membership.org).select_related(
        "customer", "shipper", "consignee", "origin", "destination", "carrier"
    )
    if membership.role == Role.CUSTOMER:
        return qs.filter(customer_id=membership.party_id) if membership.party_id else qs.none()
    if membership.role == Role.CARRIER:
        return qs.filter(carrier_id=membership.carrier_id) if membership.carrier_id else qs.none()
    return qs


def status_counts(qs: QuerySet[Shipment]) -> dict[str, int]:
    rows = qs.order_by().values("status").annotate(n=Count("id"))
    return {row["status"]: row["n"] for row in rows}


def events_for(*, shipment: Shipment, membership) -> QuerySet[TrackingEvent]:
    qs = shipment.events.select_related("location", "created_by")
    if membership.role in (Role.CUSTOMER, Role.CARRIER):
        qs = qs.filter(is_public=True)
    return qs
