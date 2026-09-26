from django.contrib import admin

from .models import ShipmentDocument


@admin.register(ShipmentDocument)
class ShipmentDocumentAdmin(admin.ModelAdmin):
    list_display = ["file_name", "doc_type", "shipment", "size", "uploaded_by", "created_at"]
    list_filter = ["doc_type"]
    search_fields = ["file_name", "shipment__reference"]
    exclude = ["content"]
    raw_id_fields = ["shipment", "trip"]
