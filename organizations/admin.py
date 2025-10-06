from django.contrib import admin
from .models import Organization, Membership

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "domain", "kind", "created_by", "created_at")
    search_fields = ("name", "domain")

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "status", "created_at")
    list_filter = ("role", "status", "organization")
    search_fields = ("user__email", "organization__domain")
