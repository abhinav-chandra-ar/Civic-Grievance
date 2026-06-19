from rest_framework import serializers
from .models import CustomUser


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
    class Meta:
        model = CustomUser
        fields = ["id", "email", "full_name", "phone", "role"]