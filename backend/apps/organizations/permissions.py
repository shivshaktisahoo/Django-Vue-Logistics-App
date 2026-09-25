"""Role-based access control. Roles are fixed in code (not DB rows) so they are
versioned, reviewable and identical across tenants. Each module owns
`<module>.<verb>` codes; views declare which code each action needs.

Row-level scoping (a customer sees only their own shipments, a carrier only their
own bids and trips) is applied separately in each module's selectors.
"""

from django.db import models


class Role(models.TextChoices):
    ADMIN = "admin", "Admin"
    OPS = "ops", "Ops Coordinator"
    CUSTOMER = "customer", "Customer"
    CARRIER = "carrier", "Carrier"


ALL = "*"

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    Role.ADMIN: frozenset({ALL}),
    Role.OPS: frozenset(
        {
            "org.view",
            "members.view",
            "masterdata.view",
            "masterdata.manage",
            "shipments.view",
            "shipments.manage",
            "shipments.book",
            "tracking.update",
            "tenders.view",
            "tenders.manage",
            "trips.view",
            "trips.manage",
            "trips.update",
            "documents.view",
            "documents.manage",
            "imports.manage",
            "exceptions.view",
            "exceptions.manage",
            "notifications.view",
            "reports.view",
            "audit.view",
        }
    ),
    Role.CUSTOMER: frozenset(
        {
            "org.view",
            "masterdata.view",
            "shipments.view",
            "shipments.book",
            "documents.view",
            "documents.manage",
            "exceptions.view",
            "reports.view",
        }
    ),
    Role.CARRIER: frozenset(
        {
            "org.view",
            "tenders.view",
            "bids.submit",
            "trips.view",
            "trips.update",
            "documents.view",
            "documents.manage",
        }
    ),
}


def role_has_perm(role: str, code: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, frozenset())
    return ALL in perms or code in perms


def permissions_for_role(role: str) -> list[str]:
    return sorted(ROLE_PERMISSIONS.get(role, frozenset()))
