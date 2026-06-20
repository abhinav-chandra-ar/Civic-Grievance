from rest_framework import serializers

from .enums import GrievanceStatus
from .models import (
    AssignmentHistory,
    Grievance,
    OfficerAssignment,
    OfficerNote,
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
            "image",
            "uploaded_at",
        )
        read_only_fields = (
            "id",
            "grievance",
            "uploaded_by",
            "uploaded_by_name",
            "uploaded_at",
        )


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
