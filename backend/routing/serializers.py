from rest_framework import serializers

from .models import Jurisdiction, RoutingRule, Ward


class WardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ward
        fields = ("id", "code", "name")


class JurisdictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Jurisdiction
        fields = ("id", "name")


class RoutingRuleSerializer(serializers.ModelSerializer):
    # Human-readable display fields (read-only)
    ward_code = serializers.CharField(source="ward.code", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    jurisdiction_name = serializers.CharField(source="jurisdiction.name", read_only=True)

    class Meta:
        model = RoutingRule
        fields = (
            "id",
            "ward",
            "ward_code",
            "category",
            "department",
            "department_name",
            "jurisdiction",
            "jurisdiction_name",
        )
