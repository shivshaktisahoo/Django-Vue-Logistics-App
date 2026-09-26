from rest_framework import serializers

from apps.core.serializers import TenantPrimaryKeyRelatedField
from apps.masterdata.models import Carrier, Vehicle
from apps.organizations.permissions import Role
from apps.shipments.models import Shipment

from .models import Bid, Tender


class LoadSerializer(serializers.Serializer):
    """What a carrier needs to price a load, without the customer's commercial details."""

    id = serializers.UUIDField()
    reference = serializers.CharField()
    status = serializers.CharField()
    service_type = serializers.CharField()
    commodity = serializers.CharField()
    total_packages = serializers.IntegerField()
    gross_weight_kg = serializers.DecimalField(max_digits=12, decimal_places=2)
    volume_cbm = serializers.DecimalField(max_digits=10, decimal_places=3)
    is_hazardous = serializers.BooleanField()
    is_temperature_controlled = serializers.BooleanField()
    origin = serializers.SerializerMethodField()
    destination = serializers.SerializerMethodField()

    def _loc(self, loc) -> dict:
        return {"code": loc.code, "name": loc.name, "city": loc.city, "country": loc.country}

    def get_origin(self, obj) -> dict:
        return self._loc(obj.origin)

    def get_destination(self, obj) -> dict:
        return self._loc(obj.destination)


class BidSerializer(serializers.ModelSerializer):
    carrier_name = serializers.CharField(source="carrier.name", read_only=True)
    carrier_code = serializers.CharField(source="carrier.code", read_only=True)

    class Meta:
        model = Bid
        fields = [
            "id",
            "carrier",
            "carrier_name",
            "carrier_code",
            "amount",
            "currency",
            "transit_hours",
            "notes",
            "status",
            "revision",
            "updated_at",
        ]
        read_only_fields = fields


class TenderSerializer(serializers.ModelSerializer):
    shipment = LoadSerializer(read_only=True)
    customer = serializers.SerializerMethodField()
    bid_count = serializers.SerializerMethodField()
    best_amount = serializers.SerializerMethodField()
    invited_count = serializers.IntegerField(read_only=True)
    target_rate = serializers.SerializerMethodField()
    my_bid = serializers.SerializerMethodField()
    awarded_to = serializers.SerializerMethodField()

    class Meta:
        model = Tender
        fields = [
            "id",
            "reference",
            "status",
            "shipment",
            "customer",
            "vehicle_type",
            "pickup_at",
            "deliver_by",
            "closes_at",
            "currency",
            "notes",
            "target_rate",
            "bid_count",
            "best_amount",
            "invited_count",
            "my_bid",
            "awarded_to",
            "cancel_reason",
            "created_at",
        ]
        read_only_fields = fields

    def _internal(self) -> bool:
        return self.context["request"].membership.role in (Role.ADMIN, Role.OPS)

    def get_customer(self, obj) -> str | None:
        return obj.shipment.customer.name if self._internal() else None

    def get_bid_count(self, obj) -> int | None:
        return getattr(obj, "bid_count", None) if self._internal() else None

    def get_best_amount(self, obj) -> str | None:
        best = getattr(obj, "best_amount", None)
        return str(best) if self._internal() and best is not None else None

    def get_target_rate(self, obj) -> str | None:
        return str(obj.target_rate) if self._internal() and obj.target_rate is not None else None

    def get_my_bid(self, obj) -> dict | None:
        membership = self.context["request"].membership
        if membership.role != Role.CARRIER:
            return None
        bid = next((b for b in obj.bids.all() if b.carrier_id == membership.carrier_id), None)
        return BidSerializer(bid).data if bid else None

    def get_awarded_to(self, obj) -> str | None:
        if obj.awarded_bid is None:
            return None
        membership = self.context["request"].membership
        if self._internal() or obj.awarded_bid.carrier_id == membership.carrier_id:
            return obj.awarded_bid.carrier.name
        return "Another carrier"


class TenderDetailSerializer(TenderSerializer):
    bids = serializers.SerializerMethodField()
    invited_carriers = serializers.SerializerMethodField()
    trip_id = serializers.SerializerMethodField()

    class Meta(TenderSerializer.Meta):
        fields = [*TenderSerializer.Meta.fields, "bids", "invited_carriers", "trip_id"]
        read_only_fields = fields

    def get_bids(self, obj) -> list[dict] | None:
        """Sealed bidding: only operations see the full field."""
        if not self._internal():
            return None
        bids = sorted(obj.bids.all(), key=lambda b: (b.status == Bid.Status.WITHDRAWN, b.amount))
        return BidSerializer(bids, many=True).data

    def get_invited_carriers(self, obj) -> list[dict] | None:
        if not self._internal():
            return None
        return [{"id": c.id, "name": c.name, "code": c.code} for c in obj.invited_carriers.all()]

    def get_trip_id(self, obj) -> str | None:
        trip = obj.trips.order_by("-created_at").first()
        if trip is None:
            return None
        membership = self.context["request"].membership
        if self._internal() or trip.carrier_id == membership.carrier_id:
            return str(trip.id)
        return None


def _road_shipments(request):
    return Shipment.objects.for_org(request.org).filter(mode="road")


def _road_carriers(request):
    return Carrier.objects.for_org(request.org).filter(mode="road", is_active=True)


class TenderCreateSerializer(serializers.Serializer):
    shipment = TenantPrimaryKeyRelatedField(model=Shipment, scope=_road_shipments)
    carriers = TenantPrimaryKeyRelatedField(model=Carrier, scope=_road_carriers, many=True)
    vehicle_type = serializers.ChoiceField(choices=Vehicle.Type.choices)
    pickup_at = serializers.DateTimeField()
    deliver_by = serializers.DateTimeField()
    closes_at = serializers.DateTimeField()
    target_rate = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class BidInputSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=1)
    transit_hours = serializers.IntegerField(min_value=1, max_value=24 * 14)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=255)


class AwardSerializer(serializers.Serializer):
    bid = serializers.UUIDField()


class TenderCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=255)
