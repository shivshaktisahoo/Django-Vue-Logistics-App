from django.db import transaction

from apps.accounts.models import User
from apps.core.exceptions import DomainError

from .models import Membership, Organization
from .permissions import Role

ORG_FIELDS = {
    "name",
    "legal_name",
    "country",
    "base_currency",
    "timezone",
    "email",
    "phone",
    "address",
}


@transaction.atomic
def create_org(*, owner: User, **data) -> Organization:
    org = Organization(owner=owner, **{k: v for k, v in data.items() if k in ORG_FIELDS})
    org.full_clean()
    org.save()
    Membership.objects.create(user=owner, org=org, role=Role.ADMIN)
    return org


@transaction.atomic
def update_org(*, org: Organization, **data) -> Organization:
    for field, value in data.items():
        if field in ORG_FIELDS:
            setattr(org, field, value)
    org.full_clean()
    org.save()
    return org


@transaction.atomic
def add_member(*, org: Organization, email: str, role: str, invited_by: User) -> Membership:
    user, _ = User.objects.get_or_create(email=email.lower())  # sets a password on first login
    membership, created = Membership.objects.get_or_create(
        user=user, org=org, defaults={"role": role, "invited_by": invited_by}
    )
    if not created:
        if membership.is_active:
            raise DomainError("This user is already a member.", field="email")
        membership.role, membership.is_active, membership.invited_by = role, True, invited_by
        membership.save()
    return membership


def change_member_role(*, membership: Membership, role: str) -> Membership:
    if membership.user_id == membership.org.owner_id:
        raise DomainError("The owner's role cannot be changed.", field="role")
    membership.role = role
    membership.save(update_fields=["role", "updated_at"])
    return membership


def remove_member(*, membership: Membership) -> None:
    if membership.user_id == membership.org.owner_id:
        raise DomainError("The owner cannot be removed.")
    membership.is_active = False
    membership.save(update_fields=["is_active", "updated_at"])
