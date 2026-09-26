from django.db.models import Count, Min, Q, QuerySet

from apps.organizations.permissions import Role

from .models import Bid, Tender


def tenders_for(*, membership) -> QuerySet[Tender]:
    qs = (
        Tender.objects.for_org(membership.org)
        .select_related(
            "shipment__origin",
            "shipment__destination",
            "shipment__customer",
            "awarded_bid__carrier",
        )
        .annotate(
            bid_count=Count(
                "bids",
                filter=Q(bids__status__in=[Bid.Status.SUBMITTED, Bid.Status.WON, Bid.Status.LOST]),
                distinct=True,
            ),
            best_amount=Min(
                "bids__amount", filter=Q(bids__status__in=[Bid.Status.SUBMITTED, Bid.Status.WON])
            ),
            invited_count=Count("invited_carriers", distinct=True),
        )
        .order_by("-created_at")
    )
    if membership.role == Role.CARRIER:
        return (
            qs.filter(invited_carriers=membership.carrier_id)
            if membership.carrier_id
            else qs.none()
        )
    return qs
