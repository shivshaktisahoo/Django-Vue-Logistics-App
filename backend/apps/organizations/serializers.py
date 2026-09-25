from rest_framework import serializers

from .models import Membership, Organization
from .permissions import Role, permissions_for_role


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "legal_name",
            "country",
            "base_currency",
            "timezone",
            "email",
            "phone",
            "address",
            "is_demo",
            "created_at",
        ]
        read_only_fields = ["id", "is_demo", "created_at"]


class MyOrgSerializer(serializers.ModelSerializer):
    """An organization as seen by the current user, including their role."""

    org = OrganizationSerializer()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = ["org", "role", "permissions"]

    def get_permissions(self, obj) -> list[str]:
        return permissions_for_role(obj.role)


class MemberSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    job_title = serializers.CharField(source="user.job_title", read_only=True)

    class Meta:
        model = Membership
        fields = ["id", "email", "full_name", "job_title", "role", "is_active", "created_at"]
        read_only_fields = ["id", "email", "full_name", "job_title", "is_active", "created_at"]


class AddMemberSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=Role.choices)
