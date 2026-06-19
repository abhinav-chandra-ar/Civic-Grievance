from rest_framework import serializers

from .models import Grievance


class GrievanceSerializer(serializers.ModelSerializer):

    citizen_name = serializers.CharField(
        source="citizen.full_name",
        read_only=True,
    )

    department_name = serializers.CharField(
        source="department.name",
        read_only=True,
    )

    class Meta:
        model = Grievance
        fields = "__all__"
        read_only_fields = (
            "citizen",
            "status",
            "priority",
            "department",
            "assigned_officer",
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
        max_bytes = 5 * 1024 * 1024  # 5 MB
        if value.size > max_bytes:
            raise serializers.ValidationError(
                "Image size cannot exceed 5 MB."
            )
        return value
