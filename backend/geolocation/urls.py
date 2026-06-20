from django.urls import path

from .views import DetectWardView

urlpatterns = [
    path("detect-ward/", DetectWardView.as_view(), name="detect-ward"),
]
