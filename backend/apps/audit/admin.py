from django.contrib import admin

from .models import AuditEntry


@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):
    list_display = ["created_at", "action", "entity_label", "actor", "org"]
    list_filter = ["action", "entity_type"]
    search_fields = ["entity_label", "summary"]

    # Append-only: the admin can read the trail but never rewrite it.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
