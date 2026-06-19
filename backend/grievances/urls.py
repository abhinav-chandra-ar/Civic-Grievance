from django.urls import path

from .views import (
    CreateGrievanceView,
    MyGrievancesView,
    GrievanceDetailView,
)

urlpatterns = [
    path("", MyGrievancesView.as_view(), name="my-grievances"),
    path("create/", CreateGrievanceView.as_view(), name="create-grievance"),
    path("<int:pk>/", GrievanceDetailView.as_view(), name="grievance-detail"),
]
