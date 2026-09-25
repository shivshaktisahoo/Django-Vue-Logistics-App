from django_filters import rest_framework as filters
from rest_framework import mixins, viewsets

from apps.core.pagination import LargeListCursorPagination
from apps.core.tenancy import TenantScopedMixin

from .models import AuditEntry
from .serializers import AuditEntrySerializer


class AuditFilter(filters.FilterSet):
    class Meta:
        model = AuditEntry
        fields = ["entity_type", "entity_id", "action"]


class AuditViewSet(TenantScopedMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = AuditEntrySerializer
    queryset = AuditEntry.objects.none()
    pagination_class = LargeListCursorPagination
    filterset_class = AuditFilter
    required_permissions = {"list": "audit.view"}

    def get_queryset(self):
        return AuditEntry.objects.for_org(self.request.org).select_related("actor")
