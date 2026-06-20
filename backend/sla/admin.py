from django.contrib import admin

from .models import GrievanceSLA, SLAPolicy


@admin.register(SLAPolicy)
class SLAPolicyAdmin(admin.ModelAdmin):
    list_display = ("id", "department", "priority", "sla_hours", "is_active", "created_at")
    list_filter = ("priority", "is_active", "department")
    ordering = ("department", "priority")


@admin.register(GrievanceSLA)
class GrievanceSLAAdmin(admin.ModelAdmin):
    list_display = (
        "id", "grievance", "sla_hours", "status",
        "started_at", "due_at", "escalation_level",
    )
    list_filter = ("status", "escalation_level")
    readonly_fields = (
        "grievance", "policy", "sla_hours",
        "started_at", "due_at",
        "status", "breached_at", "resolved_at",
        "reminder_50_sent", "reminder_75_sent", "reminder_90_sent",
        "escalation_level", "l1_escalated_at", "l2_escalated_at", "l3_escalated_at",
        "created_at", "updated_at",
    )
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
