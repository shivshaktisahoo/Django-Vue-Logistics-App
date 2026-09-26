from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.core.tenancy import TenantScopedMixin
from apps.masterdata.models import Driver, Vehicle

from . import selectors, services
from .models import Trip
from .serializers import (
    CompleteStopSerializer,
    TripAssignSerializer,
    TripCancelSerializer,
    TripSerializer,
)


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class TripFilter(filters.FilterSet):
    status = CharInFilter(field_name="status")
    shipment = filters.UUIDFilter(field_name="stops__shipment")

    class Meta:
        model = Trip
        fields = ["status", "carrier"]


class TripViewSet(
    TenantScopedMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = TripSerializer
    queryset = Trip.objects.none()
    filterset_class = TripFilter
    search_fields = [
        "reference",
        "vehicle__plate_number",
        "driver__name",
        "stops__shipment__reference",
    ]
    ordering_fields = ["planned_start", "created_at"]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    required_permissions = {
        "list": "trips.view",
        "retrieve": "trips.view",
        "assign": "trips.update",
        "arrive": "trips.update",
        "complete": "trips.update",
        "cancel": "trips.manage",
        "fleet": "trips.update",
    }

    def get_queryset(self):
        return selectors.trips_for(membership=self.request.membership).distinct()

    def _detail(self, trip):
        return Response(TripSerializer(self.get_queryset().get(pk=trip.pk)).data)

    def _stop(self, trip, stop_id):
        return get_object_or_404(trip.stops.select_related("shipment", "location"), pk=stop_id)

    @extend_schema(request=TripAssignSerializer, responses=TripSerializer)
    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        body = TripAssignSerializer(data=request.data, context=self.get_serializer_context())
        body.is_valid(raise_exception=True)
        return self._detail(
            services.assign(trip=self.get_object(), actor=request.user, **body.validated_data)
        )

    @extend_schema(request=None, responses=TripSerializer)
    @action(detail=True, methods=["post"], url_path=r"stops/(?P<stop_id>\d+)/arrive")
    def arrive(self, request, pk=None, stop_id=None):
        trip = self.get_object()
        services.arrive(trip=trip, stop=self._stop(trip, stop_id), actor=request.user)
        return self._detail(trip)

    @extend_schema(
        request={"multipart/form-data": CompleteStopSerializer}, responses=TripSerializer
    )
    @action(detail=True, methods=["post"], url_path=r"stops/(?P<stop_id>\d+)/complete")
    def complete(self, request, pk=None, stop_id=None):
        body = CompleteStopSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        trip = self.get_object()
        services.complete(
            trip=trip,
            stop=self._stop(trip, stop_id),
            actor=request.user,
            receiver_name=body.validated_data.get("receiver_name", ""),
            pod_file=body.validated_data.get("pod"),
        )
        return self._detail(trip)

    @extend_schema(responses={200: dict})
    @action(detail=True, methods=["get"])
    def fleet(self, request, pk=None):
        """The carrier's own vehicles and drivers, flagged for fit with this load."""
        trip = self.get_object()
        load_kg = sum(s.shipment.gross_weight_kg for s in trip.stops.all() if s.kind == "pickup")
        busy = dict(
            Trip.objects.filter(
                carrier=trip.carrier, status__in=[Trip.Status.DISPATCHED, Trip.Status.IN_PROGRESS]
            )
            .exclude(pk=trip.pk)
            .values_list("vehicle_id", "reference")
        )
        vehicles = [
            {
                "id": v.id,
                "plate_number": v.plate_number,
                "vehicle_type": v.vehicle_type,
                "capacity_kg": v.capacity_kg,
                "fits": v.capacity_kg >= load_kg,
                "busy_on": busy.get(v.id),
            }
            for v in Vehicle.objects.filter(carrier=trip.carrier, is_active=True).order_by(
                "plate_number"
            )
        ]
        drivers = [
            {"id": d.id, "name": d.name, "phone": d.phone}
            for d in Driver.objects.filter(carrier=trip.carrier, is_active=True).order_by("name")
        ]
        return Response({"load_kg": str(load_kg), "vehicles": vehicles, "drivers": drivers})

    @extend_schema(request=TripCancelSerializer, responses=TripSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        body = TripCancelSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        return self._detail(
            services.cancel(
                trip=self.get_object(), actor=request.user, reason=body.validated_data["reason"]
            )
        )
