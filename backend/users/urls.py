from django.urls import path
from .views import RegisterView, MeView
from rest_framework_simplejwt.views import TokenObtainPairView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("me/", MeView.as_view(), name="me"),
]