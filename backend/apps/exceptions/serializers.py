from rest_framework import serializers

from .models import ShipmentException


def _name(user) -> str | None:
    return None if user is None else (user.full_name or user.email)


class ExceptionShipmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    reference = serializers.CharField()
    status = serializers.CharField()
    mode = serializers.CharField()
    customer = serializers.CharField(source="customer.name")
    origin = serializers.CharField(source="origin.code")
    destination = serializers.CharField(source="destination.code")
    eta = serializers.DateTimeField(allow_null=True)


class ShipmentExceptionSerializer(serializers.ModelSerializer):
    shipment = ExceptionShipmentSerializer(read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    assignee_id = serializers.UUIDField(source="assignee.id", read_only=True, allow_null=True)
    assignee_name = serializers.SerializerMethodField()
    resolved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ShipmentException
        fields = [
            "id",
            "shipment",
            "kind",
            "kind_label",
            "severity",
            "status",
            "title",
            "detail",
            "detected_at",
            "assignee_id",
            "assignee_name",
            "acknowledged_at",
            "resolved_at",
            "resolved_by_name",
            "resolution_note",
            "auto_resolved",
            "updated_at",
        ]
        read_only_fields = fields

    def get_assignee_name(self, obj) -> str | None:
        return _name(obj.assignee)

    def get_resolved_by_name(self, obj) -> str | None:
        return _name(obj.resolved_by)


class AssignSerializer(serializers.Serializer):
    assignee = serializers.UUIDField()


class ResolveSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=500)
