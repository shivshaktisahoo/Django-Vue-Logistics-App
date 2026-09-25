from django.db.models import Q, QuerySet

from apps.organizations.permissions import Role

from .models import Carrier, Driver, Location, Party, Vehicle


def parties_for(*, membership) -> QuerySet[Party]:
    """Internal staff see every party; a customer only their account and address book."""
    qs = Party.objects.for_org(membership.org)
    if membership.role == Role.CUSTOMER:
        if membership.party_id is None:
            return qs.none()
        return qs.filter(Q(pk=membership.party_id) | Q(owner_id=membership.party_id))
    return qs


def locations_for(*, membership) -> QuerySet[Location]:
    return Location.objects.for_org(membership.org)


def carriers_for(*, membership) -> QuerySet[Carrier]:
    return Carrier.objects.for_org(membership.org)


def vehicles_for(*, membership) -> QuerySet[Vehicle]:
    qs = Vehicle.objects.for_org(membership.org).select_related("carrier")
    if membership.role == Role.CARRIER:
        return qs.filter(carrier_id=membership.carrier_id)
    return qs


def drivers_for(*, membership) -> QuerySet[Driver]:
    qs = Driver.objects.for_org(membership.org).select_related("carrier")
    if membership.role == Role.CARRIER:
        return qs.filter(carrier_id=membership.carrier_id)
    return qs
