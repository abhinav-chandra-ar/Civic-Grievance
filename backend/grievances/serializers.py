from rest_framework import serializers

from .models import Grievance


class GrievanceSerializer(serializers.ModelSerializer):

    citizen_name = serializers.CharField(
        source="citizen.full_name",
        read_only=True
    )

    department_name = serializers.CharField(
        source="department.name",
        read_only=True
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