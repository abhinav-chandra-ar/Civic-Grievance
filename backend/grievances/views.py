from django.shortcuts import render

# Create your views here.
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Grievance
from .serializers import GrievanceSerializer
from .permissions import IsOwnerOrAdmin


class CreateGrievanceView(
    generics.CreateAPIView
):

    serializer_class = GrievanceSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(
        self,
        serializer
    ):
        serializer.save(
            citizen=self.request.user
        )


class MyGrievancesView(
    generics.ListAPIView
):

    serializer_class = GrievanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        if self.request.user.role == "ADMIN":
            return Grievance.objects.all().order_by(
                "-created_at"
            )

        return Grievance.objects.filter(
            citizen=self.request.user
        ).order_by(
            "-created_at"
        )


class GrievanceDetailView(
    generics.RetrieveAPIView
):

    serializer_class = GrievanceSerializer
    permission_classes = [
        IsAuthenticated,
        IsOwnerOrAdmin
    ]

    queryset = Grievance.objects.all()