import uuid

from django.db import models


class UUIDModel(models.Model):
    """Public-facing UUID primary key so IDs are not enumerable across tenants."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantQuerySet(models.QuerySet):
    def for_org(self, org):
        return self.filter(org=org)


class TenantModel(UUIDModel, TimeStampedModel):
    """Base for every row owned by an organization (a freight forwarder).

    Tenant queries must go through `for_org()`; views get the org from
    `request.org` (see `apps.core.tenancy.TenantScopedMixin`).
    """

    org = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="+", db_index=True
    )

    objects = TenantQuerySet.as_manager()

    class Meta:
        abstract = True


class DocumentSeries(models.Model):
    """Gap-free, concurrency-safe reference numbers per org, document type and year.

    Incremented only through `apps.core.numbering.next_number`, which holds a row
    lock (`SELECT ... FOR UPDATE`) so two concurrent bookings never share a number.
    """

    org = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE)
    doc_type = models.CharField(max_length=20)
    year = models.PositiveSmallIntegerField()
    prefix = models.CharField(max_length=10)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "document series"
        constraints = [
            models.UniqueConstraint(fields=["org", "doc_type", "year"], name="uniq_doc_series")
        ]

    def __str__(self) -> str:
        return f"{self.prefix}-{self.year} ({self.last_number})"
