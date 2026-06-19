from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Grievance
from .serializers import GrievanceSerializer
from .permissions import IsOwnerOrAdmin


class CreateGrievanceView(generics.CreateAPIView):
    serializer_class = GrievanceSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(citizen=self.request.user)


class MyGrievancesView(generics.ListAPIView):
    serializer_class = GrievanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.role == "ADMIN":
            qs = Grievance.objects.all()
        else:
            qs = Grievance.objects.filter(citizen=user)

        status_param = self.request.query_params.get("status")
        priority_param = self.request.query_params.get("priority")

        if status_param:
            qs = qs.filter(status=status_param)
        if priority_param:
            qs = qs.filter(priority=priority_param)

        return qs.order_by("-created_at")


class GrievanceDetailView(generics.RetrieveAPIView):
    serializer_class = GrievanceSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    queryset = Grievance.objects.all()
