from django.contrib import admin

from .models import Membership, Organization


class MembershipInline(admin.TabularInline):
    model = Membership
    fk_name = "org"
    extra = 0
    raw_id_fields = ["user", "invited_by"]


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "base_currency", "is_demo", "is_active", "created_at"]
    list_filter = ["is_demo", "is_active", "country"]
    search_fields = ["name", "legal_name"]
    raw_id_fields = ["owner"]
    inlines = [MembershipInline]
