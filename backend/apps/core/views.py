from django.conf import settings
from django.db import connection
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

HealthSerializer = inline_serializer(
    "Health", fields={"status": serializers.CharField(), "service": serializers.CharField()}
)


class HealthView(APIView):
    """Liveness only. Deliberately skips the database so keep-alive pings keep the
    web dyno warm without also keeping the serverless Postgres compute awake."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses=HealthSerializer)
    def get(self, request):
        return Response({"status": "ok", "service": settings.BRAND_NAME})


class ReadinessView(APIView):
    """Readiness: the app can reach its database."""

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses=HealthSerializer)
    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return Response({"status": "ok", "service": settings.BRAND_NAME})
