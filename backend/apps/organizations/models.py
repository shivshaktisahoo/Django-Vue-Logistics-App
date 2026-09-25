from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel, UUIDModel

from .permissions import Role, role_has_perm


class Organization(UUIDModel, TimeStampedModel):
    """A tenant: one freight forwarder / 3PL and everything it owns."""

    name = models.CharField(max_length=150)
    legal_name = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=2, default="AE", help_text="ISO 3166-1 alpha-2")
    base_currency = models.CharField(max_length=3, default="USD", help_text="ISO 4217")
    timezone = models.CharField(max_length=50, default="Asia/Dubai")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="owned_orgs"
    )
    is_demo = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class Membership(UUIDModel, TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=Role.choices)
    # Row-level scope for external users: a customer-portal user acts for one customer
    # account, a carrier user for one carrier. Internal roles leave both empty.
    party = models.ForeignKey(
        "masterdata.Party", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    carrier = models.ForeignKey(
        "masterdata.Carrier", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "org"], name="uniq_membership")]

    def __str__(self) -> str:
        return f"{self.user} @ {self.org} ({self.role})"

    def has_perm(self, code: str) -> bool:
        return self.is_active and role_has_perm(self.role, code)
