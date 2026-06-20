from django.contrib import admin

from .models import Jurisdiction, RoutingRule, Ward


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


@admin.register(Jurisdiction)
class JurisdictionAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(RoutingRule)
class RoutingRuleAdmin(admin.ModelAdmin):
    list_display = ("ward", "category", "jurisdiction", "department")
    list_filter = ("category", "department", "jurisdiction")
    search_fields = ("ward__code", "ward__name", "category")
