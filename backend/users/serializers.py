from rest_framework import serializers
from .models import CustomUser

_OFFICER_ROLES = {CustomUser.Role.JUNIOR_OFFICER, CustomUser.Role.SENIOR_OFFICER}


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ["email", "full_name", "phone", "role", "password"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data["role"] = CustomUser.Role.CITIZEN  # enforce: public signup = CITIZEN only
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user


class MeSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(
        source="department.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = CustomUser
        fields = ["id", "email", "full_name", "phone", "role", "department", "department_name"]


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["full_name", "phone"]


# ---------------------------------------------------------------------------
# Admin officer management
# ---------------------------------------------------------------------------

class OfficerCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = CustomUser
        fields = ["id", "email", "full_name", "phone", "role", "department", "password"]

    def validate_role(self, value):
        if value not in _OFFICER_ROLES:
            raise serializers.ValidationError(
                "Role must be JUNIOR_OFFICER or SENIOR_OFFICER."
            )
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def to_representation(self, instance):
        return MeSerializer(instance).data


class OfficerUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["full_name", "phone", "role", "department"]

    def validate_role(self, value):
        if value not in _OFFICER_ROLES:
            raise serializers.ValidationError(
                "Role must be JUNIOR_OFFICER or SENIOR_OFFICER."
            )
        return value

    def to_representation(self, instance):
        return MeSerializer(instance).data
