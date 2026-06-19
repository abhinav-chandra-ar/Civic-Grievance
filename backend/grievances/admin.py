from django.contrib import admin

# Register your models here.
from .models import Grievance, GrievanceStatusLog


@admin.register(Grievance)
class GrievanceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "citizen",
        "department",
        "status",
        "priority",
        "created_at",
    )

    list_filter = (
        "status",
        "priority",
        "department",
    )

    search_fields = (
        "id",
        "citizen__email",
        "raw_text",
    )


@admin.register(GrievanceStatusLog)
class GrievanceStatusLogAdmin(admin.ModelAdmin):
    list_display = (
        "grievance",
        "from_status",
        "to_status",
        "changed_by",
        "changed_at",
    )

    list_filter = (
        "from_status",
        "to_status",
    )