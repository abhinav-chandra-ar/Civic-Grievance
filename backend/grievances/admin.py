from django.contrib import admin

from .models import (
    AssignmentHistory,
    Grievance,
    GrievanceStatusLog,
    OfficerAssignment,
    OfficerNote,
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
