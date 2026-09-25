from django.db.models import Count, ProtectedError
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.core.exceptions import DomainError
from apps.core.tenancy import TenantScopedMixin
from apps.organizations.permissions import Role

from . import selectors
from .models import Carrier, Driver, Location, Party, Vehicle
from .serializers import (
    CarrierSerializer,
    DriverSerializer,
    LocationSerializer,
    PartySerializer,
    VehicleSerializer,
)

READ_WRITE = {
    "list": "masterdata.view",
    "retrieve": "masterdata.view",
    "create": "masterdata.manage",
    "update": "masterdata.manage",
    "partial_update": "masterdata.manage",
    "destroy": "masterdata.manage",
}


class MasterDataViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    required_permissions = READ_WRITE
    ordering_fields = ["name", "code", "created_at"]

    def perform_create(self, serializer):
        serializer.save(org=self.request.org)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            instance.delete()
        except ProtectedError as exc:
            raise DomainError(
                f"{instance} is used by existing shipments or trips. Deactivate it instead.",
                code="in_use",
            ) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class PartyViewSet(MasterDataViewSet):
    serializer_class = PartySerializer
    queryset = Party.objects.none()
    required_permissions = {**READ_WRITE, "create": "parties.create"}
    filterset_fields = ["is_customer", "is_shipper", "is_consignee", "is_active", "country"]
    search_fields = ["name", "code", "city", "contact_name", "email"]

    def get_queryset(self):
        return selectors.parties_for(membership=self.request.membership)

    def perform_create(self, serializer):
        membership = self.request.membership
        if membership.role == Role.CUSTOMER:
            # Customers add contacts to their own address book, never billing accounts.
            if membership.party_id is None:
                raise DomainError("Your portal account is not linked to a customer yet.")
            serializer.save(org=self.request.org, owner_id=membership.party_id, is_customer=False)
        else:
            serializer.save(org=self.request.org)


class LocationViewSet(MasterDataViewSet):
    serializer_class = LocationSerializer
    queryset = Location.objects.none()
    filterset_fields = ["kind", "country", "is_active"]
    search_fields = ["code", "name", "city"]

    def get_queryset(self):
        return selectors.locations_for(membership=self.request.membership)


class CarrierViewSet(MasterDataViewSet):
    serializer_class = CarrierSerializer
    queryset = Carrier.objects.none()
    filterset_fields = ["mode", "is_active"]
    search_fields = ["name", "code"]

    def get_queryset(self):
        return selectors.carriers_for(membership=self.request.membership).annotate(
            vehicle_count=Count("vehicles", distinct=True),
            driver_count=Count("drivers", distinct=True),
        )


class VehicleViewSet(MasterDataViewSet):
    serializer_class = VehicleSerializer
    queryset = Vehicle.objects.none()
    filterset_fields = ["carrier", "vehicle_type", "is_active"]
    search_fields = ["plate_number", "carrier__name"]
    ordering_fields = ["plate_number", "capacity_kg"]

    def get_queryset(self):
        return selectors.vehicles_for(membership=self.request.membership)


class DriverViewSet(MasterDataViewSet):
    serializer_class = DriverSerializer
    queryset = Driver.objects.none()
    filterset_fields = ["carrier", "is_active"]
    search_fields = ["name", "phone", "license_number", "carrier__name"]

    def get_queryset(self):
        return selectors.drivers_for(membership=self.request.membership)
