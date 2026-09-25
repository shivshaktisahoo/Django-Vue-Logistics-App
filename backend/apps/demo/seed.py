"""Builds the public demo workspace: one forwarder org plus a user per role.

Idempotent. `reset=True` deletes the demo org (cascading to all its data) and
rebuilds it, so visitors can create and edit freely and the nightly reset brings
the showcase back to a clean, realistic state.
"""

from django.conf import settings
from django.db import transaction

from apps.accounts.models import User
from apps.accounts.services import demo_email
from apps.organizations.models import Membership, Organization
from apps.organizations.permissions import Role

DEMO_ORG_NAME = "Gulfstream Freight Forwarders"

DEMO_PEOPLE = {
    Role.ADMIN: ("Aisha Rahman", "Operations Director"),
    Role.OPS: ("Rohan Mehta", "Ops Coordinator"),
    Role.CUSTOMER: ("Laura Chen", "Logistics Manager, Nordic Home Retail"),
    Role.CARRIER: ("Omar Haddad", "Dispatch Lead, Desert Line Transport"),
}


def _demo_user(role: str) -> User:
    name, title = DEMO_PEOPLE[role]
    user, _ = User.objects.get_or_create(
        email=demo_email(role), defaults={"full_name": name, "job_title": title, "is_demo": True}
    )
    user.full_name, user.job_title, user.is_demo = name, title, True
    user.set_password(settings.DEMO_PASSWORD)
    user.save()
    return user


@transaction.atomic
def seed_demo(*, reset: bool = False) -> Organization:
    if reset:
        Organization.objects.filter(is_demo=True).delete()

    users = {role: _demo_user(role) for role in DEMO_PEOPLE}
    org, _ = Organization.objects.get_or_create(
        is_demo=True,
        defaults={
            "name": DEMO_ORG_NAME,
            "legal_name": "Gulfstream Freight Forwarders LLC",
            "country": "AE",
            "base_currency": "USD",
            "timezone": "Asia/Dubai",
            "email": "ops@gulfstream.example",
            "phone": "+971 4 555 0100",
            "address": "Jebel Ali Free Zone, Dubai, UAE",
            "owner": users[Role.ADMIN],
        },
    )
    for role, user in users.items():
        Membership.objects.update_or_create(
            user=user, org=org, defaults={"role": role, "is_active": True}
        )
    return org
