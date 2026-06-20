from django.contrib import admin

from .models import (
    AssignmentHistory,
    Grievance,
    GrievanceStatusLog,
    GrievanceTimelineEvent,
    Notification,
    OfficerAssignment,
    OfficerNote,
    ReopenRequest,
    ResolutionEvidence,
)


@admin.register(Grievance)
class GrievanceAdmin(admin.ModelAdmin):
    list_display = ("id", "citizen", "department", "status", "priority", "assigned_officer", "created_at")
    list_filter = ("status", "priority", "department")
    search_fields = ("id", "citizen__email", "raw_text")


@admin.register(GrievanceStatusLog)
class GrievanceStatusLogAdmin(admin.ModelAdmin):
    list_display = ("grievance", "from_status", "to_status", "changed_by", "changed_at")
    list_filter = ("from_status", "to_status")


@admin.register(OfficerAssignment)
class OfficerAssignmentAdmin(admin.ModelAdmin):
    list_display = ("grievance", "assigned_officer", "assigned_by", "assigned_at", "active")
    list_filter = ("active",)
    search_fields = ("grievance__id", "assigned_officer__email")


@admin.register(AssignmentHistory)
class AssignmentHistoryAdmin(admin.ModelAdmin):
    list_display = ("grievance", "from_officer", "to_officer", "changed_by", "created_at")
    search_fields = ("grievance__id",)


@admin.register(OfficerNote)
class OfficerNoteAdmin(admin.ModelAdmin):
    list_display = ("grievance", "officer", "created_at")
    search_fields = ("grievance__id", "officer__email")


@admin.register(ResolutionEvidence)
class ResolutionEvidenceAdmin(admin.ModelAdmin):
    list_display = ("grievance", "uploaded_by", "uploaded_at")
    search_fields = ("grievance__id",)


# ---------------------------------------------------------------------------
# Module 8 admin registrations
# ---------------------------------------------------------------------------

@admin.register(GrievanceTimelineEvent)
class GrievanceTimelineEventAdmin(admin.ModelAdmin):
    list_display  = ("grievance", "event_type", "created_by", "created_at")
    list_filter   = ("event_type",)
    search_fields = ("grievance__id", "description")
    readonly_fields = ("grievance", "event_type", "description", "created_by", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ("user", "notification_type", "grievance", "is_read", "created_at")
    list_filter   = ("notification_type", "is_read")
    search_fields = ("user__email", "title", "grievance__id")
    readonly_fields = (
        "user", "grievance", "notification_type",
        "title", "message", "is_read", "created_at",
    )


@admin.register(ReopenRequest)
class ReopenRequestAdmin(admin.ModelAdmin):
    list_display  = ("grievance", "requested_by", "created_at")
    search_fields = ("grievance__id", "requested_by__email")
    readonly_fields = ("grievance", "requested_by", "reason", "photo", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
