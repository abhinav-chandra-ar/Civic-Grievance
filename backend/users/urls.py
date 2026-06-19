from django.urls import path
from .views import RegisterView, MeView, GoogleLoginView
from rest_framework_simplejwt.views import TokenObtainPairView

urlpatterns = [
    path("signup/", RegisterView.as_view(), name="signup"),
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("me/", MeView.as_view(), name="me"),
    path("auth/google/", GoogleLoginView.as_view(), name="google-login"),
]