from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.tenancy import TenantScopedMixin

from . import selectors, services
from .models import Membership
from .serializers import (
    AddMemberSerializer,
    MemberSerializer,
    MyOrgSerializer,
    OrganizationSerializer,
)


class MyOrgsView(APIView):
    """Organizations the signed-in user belongs to (no X-Org-Id needed)."""

    @extend_schema(responses=MyOrgSerializer(many=True))
    def get(self, request):
        memberships = selectors.orgs_for_user(user=request.user)
        return Response(MyOrgSerializer(memberships, many=True).data)

    @extend_schema(request=OrganizationSerializer, responses={201: MyOrgSerializer})
    def post(self, request):
        serializer = OrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = services.create_org(owner=request.user, **serializer.validated_data)
        membership = selectors.get_active_membership(user=request.user, org_id=org.id)
        return Response(MyOrgSerializer(membership).data, status=status.HTTP_201_CREATED)


class CurrentOrgView(TenantScopedMixin, APIView):
    required_permissions = {"get": "org.view", "patch": "org.manage"}

    @extend_schema(responses=OrganizationSerializer)
    def get(self, request):
        return Response(OrganizationSerializer(request.org).data)

    @extend_schema(request=OrganizationSerializer, responses=OrganizationSerializer)
    def patch(self, request):
        serializer = OrganizationSerializer(request.org, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        org = services.update_org(org=request.org, **serializer.validated_data)
        return Response(OrganizationSerializer(org).data)


class MemberViewSet(
    TenantScopedMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = MemberSerializer
    queryset = Membership.objects.none()  # schema hint; real queryset is tenant-scoped
    pagination_class = None
    http_method_names = ["get", "post", "patch", "delete"]
    required_permissions = {
        "list": "members.view",
        "create": "members.manage",
        "partial_update": "members.manage",
        "destroy": "members.manage",
    }

    def get_queryset(self):
        return selectors.members_for_org(org=self.request.org)

    @extend_schema(request=AddMemberSerializer, responses={201: MemberSerializer})
    def create(self, request):
        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = services.add_member(
            org=request.org, invited_by=request.user, **serializer.validated_data
        )
        return Response(MemberSerializer(membership).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        membership = get_object_or_404(self.get_queryset(), pk=pk)
        serializer = MemberSerializer(membership, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        membership = services.change_member_role(
            membership=membership, role=serializer.validated_data.get("role", membership.role)
        )
        return Response(MemberSerializer(membership).data)

    def destroy(self, request, pk=None):
        services.remove_member(membership=get_object_or_404(self.get_queryset(), pk=pk))
        return Response(status=status.HTTP_204_NO_CONTENT)
