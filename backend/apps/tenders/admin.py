from django.contrib import admin

from .models import Bid, Tender


class BidInline(admin.TabularInline):
    model = Bid
    extra = 0
    fields = ["carrier", "amount", "currency", "transit_hours", "status", "revision"]
    readonly_fields = fields


@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    list_display = ["reference", "status", "shipment", "closes_at", "org"]
    list_filter = ["status", "vehicle_type"]
    search_fields = ["reference", "shipment__reference"]
    raw_id_fields = ["shipment", "awarded_bid"]
    inlines = [BidInline]
