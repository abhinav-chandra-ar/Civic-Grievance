from django.contrib import admin

from .models import GeolocationLog


@admin.register(GeolocationLog)
class GeolocationLogAdmin(admin.ModelAdmin):
    list_display  = ("grievance", "detection_method", "detected_ward", "accuracy_meters", "created_at")
    list_filter   = ("detection_method",)
    search_fields = ("grievance__id", "detected_ward__name", "detected_ward__code")
    readonly_fields = (
        "grievance", "submitted_lat", "submitted_lng",
        "detected_ward", "detection_method", "accuracy_meters", "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
