from rest_framework import serializers

from apps.organizations.permissions import Role

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "full_name", "job_title", "phone", "is_demo", "date_joined"]
        read_only_fields = ["id", "email", "is_demo", "date_joined"]


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class DemoLoginSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Role.choices)


class AuthResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    user = UserSerializer()
