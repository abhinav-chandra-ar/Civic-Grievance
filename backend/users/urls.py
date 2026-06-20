from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView

from .views import (
    GoogleLoginView,
    MeView,
    OfficerListCreateView,
    OfficerUpdateView,
    RegisterView,
)

urlpatterns = [
    # Public auth
    path("signup/", RegisterView.as_view(), name="signup"),
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("auth/google/", GoogleLoginView.as_view(), name="google-login"),

    # Authenticated user
    path("me/", MeView.as_view(), name="me"),

    # Admin officer management
    path("officers/", OfficerListCreateView.as_view(), name="officer-list-create"),
    path("officers/<int:pk>/", OfficerUpdateView.as_view(), name="officer-detail-update"),
]
