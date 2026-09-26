from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.core.tenancy import TenantScopedMixin
from apps.shipments import selectors as shipment_selectors
from apps.shipments.domain import ShipmentStatus
from apps.shipments.models import Shipment, TrackingEvent

from . import services

S = ShipmentStatus
IN_FLIGHT = [S.PICKED_UP, S.IN_TRANSIT, S.AT_CUSTOMS, S.OUT_FOR_DELIVERY, S.ON_HOLD]


def _loc(location) -> dict:
    return {
        "code": location.code,
        "name": location.name,
        "city": location.city,
        "country": location.country,
        "lat": float(location.latitude),
        "lng": float(location.longitude),
    }


class LivePositionSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()
    heading = serializers.IntegerField()
    progress = serializers.FloatField()
    phase = serializers.CharField()


class LiveShipmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    reference = serializers.CharField()
    tracking_number = serializers.CharField()
    status = serializers.CharField()
    mode = serializers.CharField()
    customer = serializers.CharField()
    carrier = serializers.CharField(allow_null=True)
    origin = serializers.DictField()
    destination = serializers.DictField()
    etd = serializers.DateTimeField(allow_null=True)
    eta = serializers.DateTimeField(allow_null=True)
    atd = serializers.DateTimeField(allow_null=True)
    position = LivePositionSerializer(allow_null=True)
    eta_health = serializers.CharField(allow_null=True)
    distance_km = serializers.IntegerField()
    route = serializers.ListField(child=serializers.ListField(child=serializers.FloatField()))


def _live_row(shipment: Shipment, now) -> dict:
    return {
        "id": shipment.id,
        "reference": shipment.reference,
        "tracking_number": shipment.tracking_number,
        "status": shipment.status,
        "mode": shipment.mode,
        "customer": shipment.customer.name,
        "carrier": shipment.carrier.name if shipment.carrier else None,
        "origin": _loc(shipment.origin),
        "destination": _loc(shipment.destination),
        "etd": shipment.etd,
        "eta": shipment.eta,
        "atd": shipment.atd,
        **services.live_view(shipment, now=now),
    }


class LiveMapView(TenantScopedMixin, APIView):
    """Everything currently moving, with an estimated position: the control-tower map."""

    required_permissions = {"get": "shipments.view"}

    @extend_schema(responses=LiveShipmentSerializer(many=True))
    def get(self, request):
        qs = shipment_selectors.shipments_for(membership=request.membership).filter(
            status__in=IN_FLIGHT
        )
        modes = [m for m in request.query_params.get("mode", "").split(",") if m]
        if modes:
            qs = qs.filter(mode__in=modes)
        now = timezone.now()
        return Response(
            LiveShipmentSerializer([_live_row(s, now) for s in qs[:500]], many=True).data
        )


class ShipmentRouteView(TenantScopedMixin, APIView):
    required_permissions = {"get": "shipments.view"}

    @extend_schema(responses=LiveShipmentSerializer)
    def get(self, request, pk):
        shipment = get_object_or_404(
            shipment_selectors.shipments_for(membership=request.membership), pk=pk
        )
        return Response(LiveShipmentSerializer(_live_row(shipment, timezone.now())).data)


class PublicTrackView(APIView):
    """Anyone with the tracking number can follow the cargo: no login, no commercial
    data (parties, weights, values, references and internal notes stay private)."""

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_tracking"

    @extend_schema(responses={200: dict})
    def get(self, request, tracking_number: str):
        shipment = get_object_or_404(
            Shipment.objects.select_related("org", "origin", "destination").exclude(status=S.DRAFT),
            tracking_number=tracking_number.strip().upper(),
        )
        events = (
            TrackingEvent.objects.filter(shipment=shipment, is_public=True)
            .select_related("location")
            .order_by("-occurred_at")
        )
        body = {
            "tracking_number": shipment.tracking_number,
            "status": shipment.status,
            "status_label": shipment.get_status_display(),
            "mode": shipment.mode,
            "service": shipment.get_service_type_display(),
            "forwarder": shipment.org.name,
            "origin": _loc(shipment.origin),
            "destination": _loc(shipment.destination),
            "etd": shipment.etd,
            "eta": shipment.eta,
            "atd": shipment.atd,
            "ata": shipment.ata,
            "pieces": shipment.total_packages,
            "events": [
                {
                    "code": e.code,
                    "label": e.get_code_display(),
                    "description": e.description,
                    "location": f"{e.location.city or e.location.name}, {e.location.country}"
                    if e.location
                    else None,
                    "occurred_at": e.occurred_at,
                }
                for e in events
            ],
            **services.live_view(shipment),
        }
        response = Response(body)
        response["Cache-Control"] = "public, max-age=60"
        return response
