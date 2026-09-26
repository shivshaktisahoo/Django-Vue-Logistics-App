from django.db.models import Prefetch
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.exceptions import DomainError
from apps.core.tenancy import TenantScopedMixin
from apps.organizations.permissions import Role

from . import selectors, services
from .models import Bid, Tender
from .serializers import (
    AwardSerializer,
    BidInputSerializer,
    BidSerializer,
    TenderCancelSerializer,
    TenderCreateSerializer,
    TenderDetailSerializer,
    TenderSerializer,
)


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class TenderFilter(filters.FilterSet):
    status = CharInFilter(field_name="status")

    class Meta:
        model = Tender
        fields = ["status", "shipment"]


class TenderViewSet(
    TenantScopedMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = Tender.objects.none()
    filterset_class = TenderFilter
    search_fields = ["reference", "shipment__reference", "shipment__commodity"]
    ordering_fields = ["closes_at", "created_at", "pickup_at"]
    required_permissions = {
        "list": "tenders.view",
        "retrieve": "tenders.view",
        "summary": "tenders.view",
        "create": "tenders.manage",
        "award": "tenders.manage",
        "cancel": "tenders.manage",
        "bid": "bids.submit",
        "withdraw": "bids.submit",
    }

    def get_queryset(self):
        services.close_expired(org=self.request.org)  # lazy deadline enforcement
        return selectors.tenders_for(membership=self.request.membership).prefetch_related(
            Prefetch("bids", queryset=Bid.objects.select_related("carrier")), "invited_carriers"
        )

    def get_serializer_class(self):
        return TenderSerializer if self.action == "list" else TenderDetailSerializer

    def _detail(self, tender, code=status.HTTP_200_OK):
        tender = self.get_queryset().get(pk=tender.pk)
        return Response(
            TenderDetailSerializer(tender, context=self.get_serializer_context()).data, status=code
        )

    def _carrier(self):
        carrier = self.request.membership.carrier
        if carrier is None:
            raise DomainError("Your account isn't linked to a carrier.")
        return carrier

    @extend_schema(request=TenderCreateSerializer, responses={201: TenderDetailSerializer})
    def create(self, request):
        body = TenderCreateSerializer(data=request.data, context=self.get_serializer_context())
        body.is_valid(raise_exception=True)
        tender = services.create_tender(actor=request.user, **body.validated_data)
        return self._detail(tender, status.HTTP_201_CREATED)

    @extend_schema(request=BidInputSerializer, responses=BidSerializer)
    @action(detail=True, methods=["post"])
    def bid(self, request, pk=None):
        body = BidInputSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        bid = services.submit_bid(
            tender=self.get_object(),
            carrier=self._carrier(),
            actor=request.user,
            **body.validated_data,
        )
        return Response(BidSerializer(bid).data)

    @extend_schema(request=None, responses=BidSerializer)
    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        bid = services.withdraw_bid(
            tender=self.get_object(), carrier=self._carrier(), actor=request.user
        )
        return Response(BidSerializer(bid).data)

    @extend_schema(
        request=AwardSerializer,
        responses=inline_serializer("AwardResult", fields={"trip_id": serializers.UUIDField()}),
    )
    @action(detail=True, methods=["post"])
    def award(self, request, pk=None):
        body = AwardSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        tender = self.get_object()
        bid = tender.bids.filter(pk=body.validated_data["bid"]).first()
        if bid is None:
            raise DomainError("That bid isn't on this tender.", field="bid")
        trip = services.award(tender=tender, bid=bid, actor=request.user)
        return Response({"trip_id": trip.id})

    @extend_schema(request=TenderCancelSerializer, responses=TenderDetailSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        body = TenderCancelSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        return self._detail(
            services.cancel(
                tender=self.get_object(), actor=request.user, reason=body.validated_data["reason"]
            )
        )

    @extend_schema(
        responses=inline_serializer(
            "TenderSummary",
            fields={"counts": serializers.DictField(child=serializers.IntegerField())},
        )
    )
    @action(detail=False, methods=["get"])
    def summary(self, request):
        qs = self.get_queryset()
        counts = {s: qs.filter(status=s).count() for s in Tender.Status.values}
        if request.membership.role == Role.CARRIER:
            counts["awaiting_my_bid"] = (
                qs.filter(status=Tender.Status.OPEN)
                .exclude(bids__carrier_id=request.membership.carrier_id)
                .count()
            )
        return Response({"counts": counts})
