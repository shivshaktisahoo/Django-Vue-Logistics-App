from rest_framework import serializers

from .models import AuditEntry


class AuditEntrySerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditEntry
        fields = [
            "id",
            "action",
            "entity_type",
            "entity_id",
            "entity_label",
            "summary",
            "changes",
            "actor_name",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_name(self, obj) -> str:
        if obj.actor is None:
            return "System"
        return obj.actor.full_name or obj.actor.email
