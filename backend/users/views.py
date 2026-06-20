from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from users.permissions import IsAdmin
from .models import CustomUser
from .serializers import (
    MeSerializer,
    OfficerCreateSerializer,
    OfficerUpdateSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
)

_OFFICER_ROLES = [CustomUser.Role.JUNIOR_OFFICER, CustomUser.Role.SENIOR_OFFICER]


class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MeSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(MeSerializer(request.user).data)


class GoogleLoginView(APIView):
    permission_classes = []

    def post(self, request):
        token = request.data.get("id_token")
        if not token:
            return Response(
                {"error": "id_token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
        except ValueError:
            return Response(
                {"error": "Invalid or expired Google token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        email = idinfo.get("email")
        full_name = idinfo.get("name", "")

        user, created = CustomUser.objects.get_or_create(
            email=email,
            defaults={
                "full_name": full_name,
                "role": CustomUser.Role.CITIZEN,
            },
        )

        if created:
            user.set_unusable_password()
            user.save()

        refresh = RefreshToken.for_user(user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        })


# ---------------------------------------------------------------------------
# Admin officer management
# ---------------------------------------------------------------------------

class OfficerListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/officers/  — list all JO and SO accounts
    POST /api/officers/  — create a new JO or SO with a department
    Admin only.
    """
    permission_classes = [IsAdmin]
    queryset = (
        CustomUser.objects
        .filter(role__in=_OFFICER_ROLES)
        .select_related("department")
        .order_by("role", "full_name")
    )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return OfficerCreateSerializer
        return MeSerializer


class OfficerUpdateView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/officers/<id>/  — retrieve a single officer
    PATCH /api/officers/<id>/  — update full_name, phone, role, or department
    Admin only. PUT is disabled.
    """
    permission_classes = [IsAdmin]
    http_method_names = ["get", "patch", "head", "options"]
    queryset = (
        CustomUser.objects
        .filter(role__in=_OFFICER_ROLES)
        .select_related("department")
    )

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return OfficerUpdateSerializer
        return MeSerializer
