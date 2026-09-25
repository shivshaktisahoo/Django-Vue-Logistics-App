from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter
from rest_framework.response import Response

from apps.core.exceptions import DomainError
from apps.core.tenancy import TenantScopedMixin
from apps.organizations.permissions import Role

from . import selectors, services
from .domain import ShipmentStatus
from .models import Shipment
from .serializers import (
    ShipmentDetailSerializer,
    ShipmentListSerializer,
    ShipmentWriteSerializer,
    StatusChangeSerializer,
    TrackingEventSerializer,
)


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class ShipmentFilter(filters.FilterSet):
    status = CharInFilter(field_name="status")
    mode = CharInFilter(field_name="mode")
    eta_after = filters.IsoDateTimeFilter(field_name="eta", lookup_expr="gte")
    eta_before = filters.IsoDateTimeFilter(field_name="eta", lookup_expr="lte")

    class Meta:
        model = Shipment
        fields = ["status", "mode", "customer", "carrier", "origin", "destination"]


class ShipmentViewSet(
    TenantScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Shipment.objects.none()
    filterset_class = ShipmentFilter
    search_fields = [
        "reference",
        "tracking_number",
        "house_bill",
        "master_bill",
        "customer_reference",
        "commodity",
        "customer__name",
    ]
    ordering_fields = ["created_at", "eta", "etd", "reference", "status"]
    http_method_names = ["get", "post", "patch"]
    required_permissions = {
        "list": "shipments.view",
        "retrieve": "shipments.view",
        "summary": "shipments.view",
        "create": "shipments.book",
        "partial_update": "shipments.book",
        "change_status": "shipments.book",
        "events": "shipments.view",
    }

    def get_queryset(self):
        return selectors.shipments_for(membership=self.request.membership)

    def get_serializer_class(self):
        if self.action == "list":
            return ShipmentListSerializer
        if self.action in ("create", "partial_update"):
            return ShipmentWriteSerializer
        return ShipmentDetailSerializer

    def _detail(self, shipment):
        shipment = self.get_queryset().prefetch_related("packages").get(pk=shipment.pk)
        return ShipmentDetailSerializer(shipment, context=self.get_serializer_context()).data

    def _is_manager(self):
        return self.request.membership.has_perm("shipments.manage")

    def retrieve(self, request, *args, **kwargs):
        return Response(self._detail(self.get_object()))

    @extend_schema(request=ShipmentWriteSerializer, responses={201: ShipmentDetailSerializer})
    def create(self, request, *args, **kwargs):
        serializer = ShipmentWriteSerializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        membership = request.membership
        if membership.role == Role.CUSTOMER:
            # Portal bookings are always for the user's own account, and always drafts
            # until an ops coordinator confirms them.
            if membership.party_id is None:
                raise DomainError("Your portal account is not linked to a customer yet.")
            data["customer"] = membership.party
            data["book"] = False
        elif data.get("customer") is None:
            raise DomainError("Choose the billing customer.", field="customer")
        if data.get("book") and not self._is_manager():
            raise PermissionDenied("Only operations can confirm bookings.")
        shipment = services.create_shipment(
            org=request.org, actor=request.user, packages=data.pop("packages", []), **data
        )
        return Response(self._detail(shipment), status=status.HTTP_201_CREATED)

    @extend_schema(request=ShipmentWriteSerializer, responses=ShipmentDetailSerializer)
    def partial_update(self, request, *args, **kwargs):
        shipment = self.get_object()
        if not self._is_manager() and shipment.status != ShipmentStatus.DRAFT:
            raise PermissionDenied("This booking is confirmed; contact operations to change it.")
        serializer = ShipmentWriteSerializer(
            shipment, data=request.data, partial=True, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("book", None)
        if request.membership.role == Role.CUSTOMER:
            data.pop("customer", None)
        shipment = services.update_shipment(
            shipment=shipment, actor=request.user, packages=data.pop("packages", None), **data
        )
        return Response(self._detail(shipment))

    @extend_schema(request=StatusChangeSerializer, responses=ShipmentDetailSerializer)
    @action(detail=True, methods=["post"], url_path="status")
    def change_status(self, request, pk=None):
        shipment = self.get_object()
        serializer = StatusChangeSerializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        target = serializer.validated_data["target"]
        customer_cancelling_draft = (
            request.membership.role == Role.CUSTOMER
            and shipment.status == ShipmentStatus.DRAFT
            and target == ShipmentStatus.CANCELLED
        )
        if not self._is_manager() and not customer_cancelling_draft:
            raise PermissionDenied("Your role can't change this shipment's status.")
        shipment = services.change_status(
            shipment=shipment, actor=request.user, **serializer.validated_data
        )
        return Response(self._detail(shipment))

    @extend_schema(methods=["GET"], responses=TrackingEventSerializer(many=True))
    @extend_schema(
        methods=["POST"], request=TrackingEventSerializer, responses={201: TrackingEventSerializer}
    )
    @action(detail=True, methods=["get", "post"])
    def events(self, request, pk=None):
        shipment = self.get_object()
        if request.method == "GET":
            events = selectors.events_for(shipment=shipment, membership=request.membership)
            return Response(TrackingEventSerializer(events, many=True).data)
        if not request.membership.has_perm("tracking.update"):
            raise PermissionDenied("Your role can't add milestones.")
        serializer = TrackingEventSerializer(
            data=request.data, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        event = services.add_event(
            shipment=shipment, actor=request.user, **serializer.validated_data
        )
        return Response(TrackingEventSerializer(event).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        responses=inline_serializer(
            "ShipmentSummary",
            fields={"counts": serializers.DictField(child=serializers.IntegerField())},
        )
    )
    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Status counts for the list tabs: every active filter applies except status."""
        params = request.query_params.copy()
        params.pop("status", None)
        qs = ShipmentFilter(params, queryset=self.get_queryset(), request=request).qs
        qs = SearchFilter().filter_queryset(request, qs, self)
        return Response({"counts": selectors.status_counts(qs)})
