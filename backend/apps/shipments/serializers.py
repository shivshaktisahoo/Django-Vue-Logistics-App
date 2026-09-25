from rest_framework import serializers

from apps.core.serializers import TenantPrimaryKeyRelatedField
from apps.masterdata import selectors as md
from apps.masterdata.models import Carrier, Location, Party
from apps.organizations.permissions import Role

from . import domain
from .domain import EventCode, ShipmentStatus
from .models import Package, Shipment, TrackingEvent
from .services import RESUME


def _scoped_parties(request):
    return md.parties_for(membership=request.membership)


class PartyRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Party
        fields = ["id", "name", "code", "city", "country"]


class LocationRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "code", "name", "kind", "city", "country", "latitude", "longitude"]


class CarrierRefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Carrier
        fields = ["id", "name", "code", "mode"]


class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = [
            "id",
            "kind",
            "container_type",
            "container_number",
            "seal_number",
            "quantity",
            "description",
            "weight_kg",
            "length_cm",
            "width_cm",
            "height_cm",
            "volume_cbm",
        ]
        read_only_fields = ["id", "volume_cbm"]


class ShipmentListSerializer(serializers.ModelSerializer):
    customer = PartyRefSerializer(read_only=True)
    origin = LocationRefSerializer(read_only=True)
    destination = LocationRefSerializer(read_only=True)
    carrier = CarrierRefSerializer(read_only=True)

    class Meta:
        model = Shipment
        fields = [
            "id",
            "reference",
            "tracking_number",
            "status",
            "mode",
            "service_type",
            "incoterm",
            "customer",
            "origin",
            "destination",
            "carrier",
            "etd",
            "eta",
            "atd",
            "ata",
            "commodity",
            "customer_reference",
            "total_packages",
            "gross_weight_kg",
            "chargeable_weight_kg",
            "is_hazardous",
            "is_temperature_controlled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ShipmentDetailSerializer(ShipmentListSerializer):
    shipper = PartyRefSerializer(read_only=True)
    consignee = PartyRefSerializer(read_only=True)
    packages = PackageSerializer(many=True, read_only=True)
    allowed_transitions = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta(ShipmentListSerializer.Meta):
        fields = [
            *ShipmentListSerializer.Meta.fields,
            "shipper",
            "consignee",
            "held_from_status",
            "house_bill",
            "master_bill",
            "voyage_number",
            "hs_code",
            "declared_value",
            "currency",
            "special_instructions",
            "volume_cbm",
            "packages",
            "allowed_transitions",
            "can_edit",
        ]
        read_only_fields = fields

    def _membership(self):
        return self.context["request"].membership

    def get_allowed_transitions(self, obj) -> list[str]:
        membership = self._membership()
        if membership.has_perm("shipments.manage"):
            allowed = sorted(domain.TRANSITIONS[obj.status], key=list(ShipmentStatus.values).index)
            return [*allowed, RESUME] if obj.status == ShipmentStatus.ON_HOLD else allowed
        if membership.role == Role.CUSTOMER and obj.status == ShipmentStatus.DRAFT:
            return [ShipmentStatus.CANCELLED]
        return []

    def get_can_edit(self, obj) -> bool:
        membership = self._membership()
        if membership.has_perm("shipments.manage"):
            return obj.status not in domain.TERMINAL_STATUSES
        return membership.role == Role.CUSTOMER and obj.status == ShipmentStatus.DRAFT


class ShipmentWriteSerializer(serializers.ModelSerializer):
    customer = TenantPrimaryKeyRelatedField(model=Party, scope=_scoped_parties, required=False)
    shipper = TenantPrimaryKeyRelatedField(model=Party, scope=_scoped_parties)
    consignee = TenantPrimaryKeyRelatedField(model=Party, scope=_scoped_parties)
    origin = TenantPrimaryKeyRelatedField(model=Location)
    destination = TenantPrimaryKeyRelatedField(model=Location)
    carrier = TenantPrimaryKeyRelatedField(model=Carrier, required=False, allow_null=True)
    packages = PackageSerializer(many=True, required=False)
    book = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = Shipment
        fields = [
            "mode",
            "service_type",
            "incoterm",
            "customer",
            "shipper",
            "consignee",
            "origin",
            "destination",
            "carrier",
            "etd",
            "eta",
            "house_bill",
            "master_bill",
            "voyage_number",
            "customer_reference",
            "commodity",
            "hs_code",
            "declared_value",
            "currency",
            "is_hazardous",
            "is_temperature_controlled",
            "special_instructions",
            "packages",
            "book",
        ]

    def validate_customer(self, party):
        if party is not None and not party.is_customer:
            raise serializers.ValidationError(f"{party} is not a customer account.")
        return party


class StatusChangeSerializer(serializers.Serializer):
    target = serializers.ChoiceField(choices=[*ShipmentStatus.values, RESUME])
    occurred_at = serializers.DateTimeField(required=False)
    location = TenantPrimaryKeyRelatedField(model=Location, required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)


class TrackingEventSerializer(serializers.ModelSerializer):
    location = LocationRefSerializer(read_only=True)
    location_id = TenantPrimaryKeyRelatedField(
        model=Location, source="location", write_only=True, required=False, allow_null=True
    )
    code_label = serializers.CharField(source="get_code_display", read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TrackingEvent
        fields = [
            "id",
            "code",
            "code_label",
            "description",
            "location",
            "location_id",
            "occurred_at",
            "source",
            "is_public",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = ["id", "source", "created_at"]

    def get_created_by_name(self, obj) -> str:
        if obj.created_by is None:
            return "System"
        return obj.created_by.full_name or obj.created_by.email

    def validate_code(self, code):
        if code not in EventCode.values:
            raise serializers.ValidationError("Unknown event code.")
        return code
