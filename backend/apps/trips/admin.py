from django.contrib import admin

from .models import Trip, TripStop


class StopInline(admin.TabularInline):
    model = TripStop
    extra = 0
    raw_id_fields = ["shipment", "location"]


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ["reference", "status", "carrier", "vehicle", "driver", "planned_start", "org"]
    list_filter = ["status"]
    search_fields = ["reference", "vehicle__plate_number"]
    raw_id_fields = ["carrier", "tender", "vehicle", "driver"]
    inlines = [StopInline]
