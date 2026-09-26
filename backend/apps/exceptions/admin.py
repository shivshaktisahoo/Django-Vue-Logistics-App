from django.contrib import admin

from .models import ShipmentException


@admin.register(ShipmentException)
class ShipmentExceptionAdmin(admin.ModelAdmin):
    list_display = ["title", "kind", "severity", "status", "shipment", "assignee", "detected_at"]
    list_filter = ["kind", "severity", "status", "auto_resolved"]
    search_fields = ["title", "shipment__reference"]
    raw_id_fields = ["shipment", "assignee", "resolved_by"]
