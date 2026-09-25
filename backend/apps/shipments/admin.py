from django.contrib import admin

from .models import Package, Shipment, TrackingEvent


class PackageInline(admin.TabularInline):
    model = Package
    extra = 0


class TrackingEventInline(admin.TabularInline):
    model = TrackingEvent
    fk_name = "shipment"
    extra = 0
    fields = ["code", "description", "location", "occurred_at", "source", "is_public"]
    raw_id_fields = ["location"]


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = [
        "reference",
        "status",
        "mode",
        "customer",
        "origin",
        "destination",
        "eta",
        "org",
    ]
    list_filter = ["status", "mode", "service_type"]
    search_fields = ["reference", "tracking_number", "house_bill", "master_bill"]
    raw_id_fields = ["customer", "shipper", "consignee", "origin", "destination", "carrier"]
    readonly_fields = ["reference", "tracking_number", "status", "held_from_status"]
    inlines = [PackageInline, TrackingEventInline]
