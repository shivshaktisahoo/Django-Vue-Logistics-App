from django.contrib import admin

from .models import Carrier, Driver, Location, Party, Vehicle


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_customer", "is_shipper", "is_consignee", "country", "org"]
    list_filter = ["is_customer", "is_shipper", "is_consignee", "country"]
    search_fields = ["name", "code"]
    raw_id_fields = ["owner"]


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "kind", "country", "org"]
    list_filter = ["kind", "country"]
    search_fields = ["code", "name", "city"]


@admin.register(Carrier)
class CarrierAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "mode", "org"]
    list_filter = ["mode"]
    search_fields = ["name", "code"]


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ["plate_number", "vehicle_type", "capacity_kg", "carrier"]
    list_filter = ["vehicle_type"]


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ["name", "phone", "carrier"]
