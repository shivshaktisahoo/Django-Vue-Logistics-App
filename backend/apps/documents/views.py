from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.core.tenancy import TenantScopedMixin
from apps.organizations.permissions import Role
from apps.shipments import selectors as shipment_selectors

from . import services
from .models import ShipmentDocument


class DocumentSerializer(serializers.ModelSerializer):
    doc_type_label = serializers.CharField(source="get_doc_type_display", read_only=True)
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ShipmentDocument
        fields = [
            "id",
            "shipment",
            "trip",
            "doc_type",
            "doc_type_label",
            "file_name",
            "content_type",
            "size",
            "notes",
            "visible_to_customer",
            "uploaded_by",
            "uploaded_by_name",
            "created_at",
        ]
        read_only_fields = fields

    def get_uploaded_by_name(self, obj) -> str:
        return (
            "System"
            if obj.uploaded_by is None
            else (obj.uploaded_by.full_name or obj.uploaded_by.email)
        )


class UploadSerializer(serializers.Serializer):
    shipment = serializers.UUIDField()
    doc_type = serializers.ChoiceField(choices=ShipmentDocument.DocType.choices)
    file = serializers.FileField()
    notes = serializers.CharField(required=False, allow_blank=True, max_length=255)
    visible_to_customer = serializers.BooleanField(required=False, default=True)


class DocumentViewSet(
    TenantScopedMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = DocumentSerializer
    queryset = ShipmentDocument.objects.none()
    parser_classes = [MultiPartParser, FormParser]
    pagination_class = None
    filterset_fields = ["shipment", "trip", "doc_type"]
    required_permissions = {
        "list": "documents.view",
        "download": "documents.view",
        "create": "documents.manage",
        "destroy": "documents.manage",
    }

    def get_queryset(self):
        membership = self.request.membership
        shipments = shipment_selectors.shipments_for(membership=membership).values("pk")
        qs = (
            ShipmentDocument.objects.for_org(self.request.org)
            .filter(shipment__in=shipments)
            .select_related("uploaded_by")
            .defer("content")  # never pull file bytes into list queries
        )
        if membership.role == Role.CUSTOMER:
            qs = qs.filter(visible_to_customer=True)
        return qs

    @extend_schema(
        request={"multipart/form-data": UploadSerializer}, responses={201: DocumentSerializer}
    )
    def create(self, request, *args, **kwargs):
        body = UploadSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        data = body.validated_data
        membership = request.membership
        shipment = get_object_or_404(
            shipment_selectors.shipments_for(membership=membership), pk=data["shipment"]
        )
        visible = data["visible_to_customer"] if membership.role in (Role.ADMIN, Role.OPS) else True
        doc = services.upload(
            shipment=shipment,
            actor=request.user,
            file=data["file"],
            doc_type=data["doc_type"],
            notes=data.get("notes", ""),
            visible_to_customer=visible,
        )
        return Response(DocumentSerializer(doc).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        doc = self.get_object()
        internal = request.membership.role in (Role.ADMIN, Role.OPS)
        if not internal and doc.uploaded_by_id != request.user.id:
            raise PermissionDenied("You can only delete documents you uploaded.")
        services.delete(doc=doc, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(responses={(200, "application/octet-stream"): OpenApiTypes.BINARY})
    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        doc = get_object_or_404(self.get_queryset().defer(None), pk=pk)
        response = HttpResponse(bytes(doc.content), content_type=doc.content_type)
        disposition = "inline" if request.query_params.get("inline") else "attachment"
        response["Content-Disposition"] = f'{disposition}; filename="{doc.file_name}"'
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, max-age=300"
        return response
