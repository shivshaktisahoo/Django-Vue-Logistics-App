from django.db.models import Count, Q
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.tenancy import TenantScopedMixin

from . import detection, selectors, services
from .models import ShipmentException as Exc
from .serializers import AssignSerializer, ResolveSerializer, ShipmentExceptionSerializer


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class ExceptionFilter(filters.FilterSet):
    status = CharInFilter(field_name="status")
    severity = CharInFilter(field_name="severity")
    kind = CharInFilter(field_name="kind")
    mine = filters.BooleanFilter(method="filter_mine")

    class Meta:
        model = Exc
        fields = ["status", "severity", "kind", "shipment"]

    def filter_mine(self, qs, name, value):
        return qs.filter(assignee=self.request.user) if value else qs


class ExceptionViewSet(
    TenantScopedMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = ShipmentExceptionSerializer
    queryset = Exc.objects.none()
    filterset_class = ExceptionFilter
    search_fields = ["title", "shipment__reference", "shipment__customer__name"]
    ordering_fields = ["detected_at", "severity"]
    required_permissions = {
        "list": "exceptions.view",
        "retrieve": "exceptions.view",
        "summary": "exceptions.view",
        "acknowledge": "exceptions.manage",
        "assign": "exceptions.manage",
        "resolve": "exceptions.manage",
        "scan": "exceptions.manage",
    }

    def get_queryset(self):
        return selectors.exceptions_for(membership=self.request.membership)

    def _respond(self, exc):
        return Response(ShipmentExceptionSerializer(self.get_queryset().get(pk=exc.pk)).data)

    @extend_schema(request=None, responses=ShipmentExceptionSerializer)
    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        return self._respond(services.acknowledge(exc=self.get_object(), actor=request.user))

    @extend_schema(request=AssignSerializer, responses=ShipmentExceptionSerializer)
    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        body = AssignSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        exc = services.assign(
            exc=self.get_object(), assignee_id=body.validated_data["assignee"], actor=request.user
        )
        return self._respond(exc)

    @extend_schema(request=ResolveSerializer, responses=ShipmentExceptionSerializer)
    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        body = ResolveSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        return self._respond(
            services.resolve(
                exc=self.get_object(), actor=request.user, note=body.validated_data["note"]
            )
        )

    @extend_schema(
        responses=inline_serializer(
            "ExceptionSummary",
            fields={
                "open": serializers.IntegerField(),
                "acknowledged": serializers.IntegerField(),
                "critical": serializers.IntegerField(),
                "high": serializers.IntegerField(),
                "mine": serializers.IntegerField(),
            },
        )
    )
    @action(detail=False, methods=["get"])
    def summary(self, request):
        unresolved = ~Q(status=Exc.Status.RESOLVED)
        return Response(
            self.get_queryset().aggregate(
                open=Count("id", filter=Q(status=Exc.Status.OPEN)),
                acknowledged=Count("id", filter=Q(status=Exc.Status.ACKNOWLEDGED)),
                critical=Count("id", filter=unresolved & Q(severity=Exc.Severity.CRITICAL)),
                high=Count("id", filter=unresolved & Q(severity=Exc.Severity.HIGH)),
                mine=Count("id", filter=unresolved & Q(assignee=request.user)),
            )
        )

    @extend_schema(
        request=None,
        responses=inline_serializer("ScanResult", fields={"scanned": serializers.IntegerField()}),
    )
    @action(detail=False, methods=["post"])
    def scan(self, request):
        """Run the rule engine now instead of waiting for the hourly job."""
        return Response(detection.scan(org=request.org))
