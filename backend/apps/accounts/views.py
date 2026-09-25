"""Auth endpoints.

The access token is returned in the body and kept in memory by the SPA. The refresh
token lives in an httpOnly cookie scoped to /api/v1/auth/, so it can't be read by
JavaScript (XSS) and is only sent to the refresh/logout endpoints. In production the
SPA's host proxies /api to this service, so the cookie is first-party.
"""

import contextlib

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from . import services
from .models import User
from .serializers import (
    AuthResponseSerializer,
    DemoLoginSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)


def _set_refresh_cookie(response: Response, refresh: str) -> None:
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite="Lax",
        path=settings.REFRESH_COOKIE_PATH,
    )


def _auth_response(user, *, status_code=status.HTTP_200_OK) -> Response:
    tokens = services.issue_tokens(user)
    response = Response(
        {"access": tokens["access"], "user": UserSerializer(user).data}, status=status_code
    )
    _set_refresh_cookie(response, tokens["refresh"])
    return response


class PublicAuthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class RegisterView(PublicAuthView):
    @extend_schema(request=RegisterSerializer, responses={201: AuthResponseSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.register_user(**serializer.validated_data)
        return _auth_response(user, status_code=status.HTTP_201_CREATED)


class LoginView(PublicAuthView):
    @extend_schema(request=LoginSerializer, responses=AuthResponseSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.login_with_password(**serializer.validated_data)
        return _auth_response(user)


class DemoLoginView(PublicAuthView):
    @extend_schema(request=DemoLoginSerializer, responses=AuthResponseSerializer)
    def post(self, request):
        serializer = DemoLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.demo_user_for_role(**serializer.validated_data)
        return _auth_response(user)


class RefreshView(PublicAuthView):
    throttle_classes = []

    @extend_schema(request=None, responses={200: AuthResponseSerializer, 204: None})
    def post(self, request):
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if not raw:
            # No session at all is a normal state for a first visit, not an error:
            # 204 keeps the SPA's startup check from logging a failed request.
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = TokenRefreshSerializer(data={"refresh": raw})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError:
            return Response({"detail": "Session expired."}, status=status.HTTP_401_UNAUTHORIZED)
        user_id = RefreshToken(serializer.validated_data["refresh"])["user_id"]
        user = User.objects.filter(pk=user_id, is_active=True).first()
        if user is None:
            return Response({"detail": "Session expired."}, status=status.HTTP_401_UNAUTHORIZED)
        response = Response(
            {"access": serializer.validated_data["access"], "user": UserSerializer(user).data}
        )
        _set_refresh_cookie(response, serializer.validated_data["refresh"])
        return response


class LogoutView(PublicAuthView):
    throttle_classes = []

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
        if raw:
            with contextlib.suppress(TokenError):
                RefreshToken(raw).blacklist()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(settings.REFRESH_COOKIE_NAME, path=settings.REFRESH_COOKIE_PATH)
        return response


class MeView(APIView):
    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(request=UserSerializer, responses=UserSerializer)
    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
