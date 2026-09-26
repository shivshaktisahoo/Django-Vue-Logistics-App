from rest_framework import serializers

from apps.core.serializers import TenantPrimaryKeyRelatedField
from apps.masterdata.models import Driver, Vehicle

from .models import Trip, TripStop


class StopSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    shipment = serializers.SerializerMethodField()
    party = serializers.SerializerMethodField()

    class Meta:
        model = TripStop
        fields = [
            "id",
            "sequence",
            "kind",
            "location",
            "shipment",
            "party",
            "planned_at",
            "arrived_at",
            "completed_at",
            "receiver_name",
        ]
        read_only_fields = fields

    def get_location(self, obj) -> dict:
        loc = obj.location
        return {"code": loc.code, "name": loc.name, "city": loc.city, "country": loc.country}

    def get_shipment(self, obj) -> dict:
        s = obj.shipment
        return {
            "id": s.id,
            "reference": s.reference,
            "status": s.status,
            "commodity": s.commodity,
            "total_packages": s.total_packages,
            "gross_weight_kg": str(s.gross_weight_kg),
            "is_hazardous": s.is_hazardous,
            "is_temperature_controlled": s.is_temperature_controlled,
        }

    def get_party(self, obj) -> dict:
        """Who the driver meets at this stop: the shipper at pickup, consignee at delivery."""
        p = obj.shipment.shipper if obj.kind == TripStop.Kind.PICKUP else obj.shipment.consignee
        return {"name": p.name, "contact": p.contact_name, "phone": p.phone, "city": p.city}


class TripSerializer(serializers.ModelSerializer):
    carrier = serializers.SerializerMethodField()
    vehicle = serializers.SerializerMethodField()
    driver = serializers.SerializerMethodField()
    tender = serializers.SerializerMethodField()
    stops = StopSerializer(many=True, read_only=True)
    next_stop_id = serializers.SerializerMethodField()
    load_kg = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = [
            "id",
            "reference",
            "status",
            "carrier",
            "vehicle",
            "driver",
            "tender",
            "agreed_rate",
            "currency",
            "planned_start",
            "planned_end",
            "started_at",
            "completed_at",
            "notes",
            "stops",
            "next_stop_id",
            "load_kg",
        ]
        read_only_fields = fields

    def get_carrier(self, obj) -> dict:
        return {"id": obj.carrier.id, "name": obj.carrier.name, "code": obj.carrier.code}

    def get_vehicle(self, obj) -> dict | None:
        v = obj.vehicle
        return (
            None
            if v is None
            else {
                "id": v.id,
                "plate_number": v.plate_number,
                "vehicle_type": v.vehicle_type,
                "capacity_kg": v.capacity_kg,
            }
        )

    def get_driver(self, obj) -> dict | None:
        d = obj.driver
        return None if d is None else {"id": d.id, "name": d.name, "phone": d.phone}

    def get_tender(self, obj) -> dict | None:
        t = obj.tender
        return None if t is None else {"id": t.id, "reference": t.reference}

    def get_next_stop_id(self, obj) -> str | None:
        if obj.status not in (Trip.Status.DISPATCHED, Trip.Status.IN_PROGRESS):
            return None
        nxt = next((s for s in obj.stops.all() if s.completed_at is None), None)
        return str(nxt.id) if nxt else None

    def get_load_kg(self, obj) -> str:
        return str(
            sum(
                s.shipment.gross_weight_kg
                for s in obj.stops.all()
                if s.kind == TripStop.Kind.PICKUP
            )
        )


def _carrier_scope(model):
    def scope(request):
        qs = model.objects.for_org(request.org).filter(is_active=True)
        carrier_id = request.membership.carrier_id
        return qs.filter(carrier_id=carrier_id) if carrier_id else qs

    return scope


class TripAssignSerializer(serializers.Serializer):
    vehicle = TenantPrimaryKeyRelatedField(model=Vehicle, scope=_carrier_scope(Vehicle))
    driver = TenantPrimaryKeyRelatedField(model=Driver, scope=_carrier_scope(Driver))


class CompleteStopSerializer(serializers.Serializer):
    receiver_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    pod = serializers.FileField(required=False)


class TripCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)
