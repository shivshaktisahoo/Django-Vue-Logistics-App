from rest_framework import serializers

from apps.core.serializers import TenantPrimaryKeyRelatedField

from .models import Carrier, Driver, Location, Party, Vehicle


class UpperCaseMixin:
    upper_fields: tuple[str, ...] = ()

    def to_internal_value(self, data):
        data = data.copy() if hasattr(data, "copy") else dict(data)
        for field in self.upper_fields:
            if isinstance(data.get(field), str):
                data[field] = data[field].strip().upper()
        return super().to_internal_value(data)


class PartySerializer(UpperCaseMixin, serializers.ModelSerializer):
    upper_fields = ("code", "country")

    class Meta:
        model = Party
        fields = [
            "id",
            "name",
            "code",
            "is_customer",
            "is_shipper",
            "is_consignee",
            "owner",
            "contact_name",
            "email",
            "phone",
            "address",
            "city",
            "country",
            "tax_id",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "owner", "created_at"]
        validators = []  # (org, code) uniqueness is checked in validate() with the tenant

    def validate(self, attrs):
        org = self.context["request"].org
        code = attrs.get("code")
        if code:
            clash = Party.objects.for_org(org).filter(code=code)
            if self.instance:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError({"code": "This code is already in use."})
        return attrs


class LocationSerializer(UpperCaseMixin, serializers.ModelSerializer):
    upper_fields = ("code", "country")

    class Meta:
        model = Location
        fields = [
            "id",
            "code",
            "name",
            "kind",
            "city",
            "country",
            "latitude",
            "longitude",
            "timezone",
            "is_active",
        ]
        read_only_fields = ["id"]
        validators = []

    def validate(self, attrs):
        org = self.context["request"].org
        code = attrs.get("code")
        if code:
            clash = Location.objects.for_org(org).filter(code=code)
            if self.instance:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError({"code": "This location code already exists."})
        return attrs


class CarrierSerializer(UpperCaseMixin, serializers.ModelSerializer):
    upper_fields = ("code", "country")
    vehicle_count = serializers.IntegerField(read_only=True, default=0)
    driver_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Carrier
        fields = [
            "id",
            "name",
            "code",
            "mode",
            "email",
            "phone",
            "country",
            "is_active",
            "vehicle_count",
            "driver_count",
        ]
        read_only_fields = ["id"]
        validators = []

    def validate(self, attrs):
        org = self.context["request"].org
        code = attrs.get("code")
        if code:
            clash = Carrier.objects.for_org(org).filter(code=code)
            if self.instance:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError({"code": "This carrier code already exists."})
        return attrs


class VehicleSerializer(UpperCaseMixin, serializers.ModelSerializer):
    upper_fields = ("plate_number",)
    carrier = TenantPrimaryKeyRelatedField(model=Carrier)
    carrier_name = serializers.CharField(source="carrier.name", read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            "id",
            "carrier",
            "carrier_name",
            "plate_number",
            "vehicle_type",
            "capacity_kg",
            "is_active",
        ]
        read_only_fields = ["id"]
        validators = []

    def validate(self, attrs):
        org = self.context["request"].org
        plate = attrs.get("plate_number")
        if plate:
            clash = Vehicle.objects.for_org(org).filter(plate_number=plate)
            if self.instance:
                clash = clash.exclude(pk=self.instance.pk)
            if clash.exists():
                raise serializers.ValidationError(
                    {"plate_number": "This plate is already registered."}
                )
        return attrs


class DriverSerializer(serializers.ModelSerializer):
    carrier = TenantPrimaryKeyRelatedField(model=Carrier)
    carrier_name = serializers.CharField(source="carrier.name", read_only=True)

    class Meta:
        model = Driver
        fields = ["id", "carrier", "carrier_name", "name", "phone", "license_number", "is_active"]
        read_only_fields = ["id"]
