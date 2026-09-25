import uuid

from django.db.models import QuerySet

from .models import Membership, Organization


def orgs_for_user(*, user) -> QuerySet[Membership]:
    return (
        Membership.objects.filter(user=user, is_active=True, org__is_active=True)
        .select_related("org")
        .order_by("org__name")
    )


def get_active_membership(*, user, org_id) -> Membership | None:
    try:
        org_id = uuid.UUID(str(org_id))
    except ValueError:
        return None
    return (
        Membership.objects.filter(user=user, org_id=org_id, is_active=True, org__is_active=True)
        .select_related("org")
        .first()
    )


def members_for_org(*, org: Organization) -> QuerySet[Membership]:
    return Membership.objects.filter(org=org).select_related("user").order_by("created_at")
