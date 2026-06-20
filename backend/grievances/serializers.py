from rest_framework import serializers

from .enums import GrievanceStatus, NotificationType
from .models import (
    AssignmentHistory,
    Grievance,
    GrievanceTimelineEvent,
    Notification,
    OfficerAssignment,
    OfficerNote,
    ReopenRequest,
    ResolutionEvidence,
)


# ---------------------------------------------------------------------------
# Supporting serializers (declared first — referenced by GrievanceSerializer)
# ---------------------------------------------------------------------------

class OfficerAssignmentSerializer(serializers.ModelSerializer):
    officer_name = serializers.CharField(
        source="assigned_officer.full_name",
        read_only=True,
    )
    assigned_by_name = serializers.CharField(
        source="assigned_by.full_name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = OfficerAssignment
        fields = (
            "id",
            "assigned_officer",
            "officer_name",
            "assigned_by",
            "assigned_by_name",
            "assigned_at",
            "active",
        )
        read_only_fields = fields


class AssignmentHistorySerializer(serializers.ModelSerializer):
    from_officer_name = serializers.CharField(
        source="from_officer.full_name",
        read_only=True,
        allow_null=True,
    )
    to_officer_name = serializers.CharField(
        source="to_officer.full_name",
        read_only=True,
    )
    changed_by_name = serializers.CharField(
        source="changed_by.full_name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = AssignmentHistory
        fields = (
            "id",
            "from_officer",
            "from_officer_name",
            "to_officer",
            "to_officer_name",
            "changed_by",
            "changed_by_name",
            "remarks",
            "created_at",
        )
        read_only_fields = fields


class OfficerNoteSerializer(serializers.ModelSerializer):
    officer_name = serializers.CharField(
        source="officer.full_name",
        read_only=True,
    )

    class Meta:
        model = OfficerNote
        fields = ("id", "grievance", "officer", "officer_name", "note", "created_at")
        read_only_fields = ("id", "grievance", "officer", "officer_name", "created_at")


class ResolutionEvidenceSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(
        source="uploaded_by.full_name",
        read_only=True,
    )

    class Meta:
        model = ResolutionEvidence
        fields = (
            "id",
            "grievance",
            "uploaded_by",
            "uploaded_by_name",
            # original single-image field (kept for backward compatibility)
            "image",
            # Module 8 additions
            "before_image",
            "after_image",
            "resolution_notes",
            "uploaded_at",
        )
        read_only_fields = (
            "id",
            "grievance",
            "uploaded_by",
            "uploaded_by_name",
            "uploaded_at",
        )
        # before_image, after_image, resolution_notes are writable by officers.


# ---------------------------------------------------------------------------
# Grievance serializer
# ---------------------------------------------------------------------------

class GrievanceSerializer(serializers.ModelSerializer):
    citizen_name = serializers.CharField(
        source="citizen.full_name",
        read_only=True,
    )
    ward_name = serializers.CharField(
        source="ward.name",
        read_only=True,
        allow_null=True,
    )
    department_name = serializers.CharField(
        source="department.name",
        read_only=True,
        allow_null=True,
    )
    jurisdiction_name = serializers.CharField(
        source="jurisdiction.name",
        read_only=True,
        allow_null=True,
    )
    assignment = OfficerAssignmentSerializer(read_only=True)

    # GPS coordinates — write-only, not stored on Grievance.
    # Consumed in CreateGrievanceView.perform_create and popped before save().
    latitude = serializers.FloatField(
        write_only=True,
        required=False,
        min_value=8.0,
        max_value=9.0,
        help_text="WGS84 latitude (Trivandrum Corporation bounding box: 8.0 - 9.0).",
    )
    longitude = serializers.FloatField(
        write_only=True,
        required=False,
        min_value=76.5,
        max_value=77.5,
        help_text="WGS84 longitude (Trivandrum Corporation bounding box: 76.5 - 77.5).",
    )

    class Meta:
        model = Grievance
        fields = "__all__"
        read_only_fields = (
            "citizen",
            "status",
            "priority",
            "department",           # set by routing service
            "jurisdiction",         # set by routing service
            "assignment",           # set by assignment service
            "assigned_officer",     # denormalized cache, set by assignment service
            "assigned_at",
            "resolved_by",
            "created_at",
            "updated_at",
            "ml_translated_text",
            "ml_summary",
            "ml_department_suggestion",
            "ml_priority_suggestion",
            "ml_is_spam",
            "ml_is_duplicate",
            "ml_duplicate_type",
            "ml_image_valid",
            "ml_location_extracted",
            "ml_processed_at",
        )

    def validate_raw_text(self, value):
        stripped = value.strip()
        if len(stripped) < 20:
            raise serializers.ValidationError(
                "Grievance description must be at least 20 characters."
            )
        if len(stripped) > 2000:
            raise serializers.ValidationError(
                "Grievance description cannot exceed 2000 characters."
            )
        return value

    def validate_image(self, value):
        if value is None:
            return value
        allowed_types = {"image/jpeg", "image/png", "image/webp"}
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                "Only JPEG, PNG, and WEBP images are allowed."
            )
        max_bytes = 5 * 1024 * 1024
        if value.size > max_bytes:
            raise serializers.ValidationError("Image size cannot exceed 5 MB.")
        return value

    def validate(self, data):
        lat  = data.get("latitude")
        lng  = data.get("longitude")
        ward = data.get("ward")

        # Rule 1 — GPS coordinates must be provided as a complete pair.
        if (lat is None) != (lng is None):
            raise serializers.ValidationError(
                "latitude and longitude must both be provided together."
            )

        # Rule 2 — Mandatory ward enforcement.
        # At least one of GPS coordinates or a manual ward FK must be present.
        if lat is None and ward is None:
            raise serializers.ValidationError(
                "Ward is required. Provide GPS coordinates (latitude + longitude) "
                "or select a ward manually."
            )

        return data


# ---------------------------------------------------------------------------
# Action-specific input serializers
# ---------------------------------------------------------------------------

class AssignOfficerSerializer(serializers.Serializer):
    officer_id = serializers.IntegerField()


class ReassignOfficerSerializer(serializers.Serializer):
    officer_id = serializers.IntegerField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class StatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=GrievanceStatus.choices)


# ---------------------------------------------------------------------------
# Module 8 serializers
# ---------------------------------------------------------------------------

class GrievanceTimelineEventSerializer(serializers.ModelSerializer):
    """Read-only view of a single lifecycle event on a grievance timeline."""

    created_by_name = serializers.CharField(
        source="created_by.full_name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = GrievanceTimelineEvent
        fields = (
            "id",
            "event_type",
            "description",
            "created_by",
            "created_by_name",
            "created_at",
        )
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    """
    Citizen/officer notification.
    `is_read` is the only writable field — updated via the
    POST /api/notifications/{id}/read/ endpoint (Phase 3).
    """

    class Meta:
        model = Notification
        fields = (
            "id",
            "grievance",
            "notification_type",
            "title",
            "message",
            "is_read",
            "created_at",
        )
        read_only_fields = (
            "id",
            "grievance",
            "notification_type",
            "title",
            "message",
            "created_at",
        )
        # is_read is intentionally writable so the read endpoint can flip it.


class ReopenRequestSerializer(serializers.ModelSerializer):
    """
    Citizen-submitted reopen request.
    `reason` is required; `photo` is optional.
    `grievance`, `requested_by`, and `created_at` are set by the view.
    """

    requested_by_name = serializers.CharField(
        source="requested_by.full_name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = ReopenRequest
        fields = (
            "id",
            "grievance",
            "reason",
            "photo",
            "requested_by",
            "requested_by_name",
            "created_at",
        )
        read_only_fields = (
            "id",
            "grievance",
            "requested_by",
            "requested_by_name",
            "created_at",
        )
        # reason and photo are writable; photo is optional (model allows null).
