from django.db.models import QuerySet

from apps.organizations.permissions import Role

from .models import ShipmentException


def exceptions_for(*, membership) -> QuerySet[ShipmentException]:
    qs = ShipmentException.objects.for_org(membership.org).select_related(
        "shipment__origin", "shipment__destination", "shipment__customer", "assignee", "resolved_by"
    )
    if membership.role == Role.CUSTOMER:
        return (
            qs.filter(shipment__customer_id=membership.party_id)
            if membership.party_id
            else qs.none()
        )
    if membership.role == Role.CARRIER:
        return (
            qs.filter(shipment__carrier_id=membership.carrier_id)
            if membership.carrier_id
            else qs.none()
        )
    return qs
