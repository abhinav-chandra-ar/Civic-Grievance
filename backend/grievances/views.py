import logging

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import CustomUser
from .enums import GrievanceStatus
from .models import Grievance, OfficerNote, ResolutionEvidence
from .permissions import IsOfficer, IsOwnerOrAdmin, IsSeniorOfficerOrAdmin
from .serializers import (
    AssignmentHistorySerializer,
    AssignOfficerSerializer,
    GrievanceSerializer,
    OfficerNoteSerializer,
    ReassignOfficerSerializer,
    ResolutionEvidenceSerializer,
    StatusUpdateSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Citizen-facing
# ---------------------------------------------------------------------------

class CreateGrievanceView(generics.CreateAPIView):
    serializer_class = GrievanceSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        grievance = serializer.save(citizen=self.request.user)
        try:
            from ml_engine.pipeline import run_ml_pipeline
            run_ml_pipeline(grievance)
        except Exception:
            logger.exception(
                "ML pipeline failed for grievance #%s -- grievance saved, ml_* fields blank",
                grievance.id,
            )
        try:
            from routing.service import run_routing
            run_routing(grievance)
        except Exception:
            logger.exception(
                "Routing failed for grievance #%s -- department and jurisdiction not assigned",
                grievance.id,
            )


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


# ---------------------------------------------------------------------------
# Officer dashboard & department queue
# ---------------------------------------------------------------------------

class OfficerDashboardView(generics.ListAPIView):
    """
    GET /api/officer/grievances/
    Returns active cases assigned to the requesting officer.
    """
    serializer_class = GrievanceSerializer
    permission_classes = [IsOfficer]

    def get_queryset(self):
        terminal = {GrievanceStatus.CLOSED, GrievanceStatus.REJECTED}
        return (
            Grievance.objects
            .filter(assigned_officer=self.request.user)
            .exclude(status__in=terminal)
            .order_by("-created_at")
        )


class DepartmentQueueView(generics.ListAPIView):
    """
    GET /api/departments/<dept_pk>/queue/
    Returns SUBMITTED unassigned grievances for a department.
    - ADMIN: any department.
    - SENIOR_OFFICER: own department only (403 otherwise).
    - JUNIOR_OFFICER / CITIZEN: 403 via IsSeniorOfficerOrAdmin.
    """
    serializer_class = GrievanceSerializer
    permission_classes = [IsSeniorOfficerOrAdmin]

    def get_queryset(self):
        dept_pk = self.kwargs["dept_pk"]
        user = self.request.user

        if user.role == "SENIOR_OFFICER" and user.department_id != dept_pk:
            raise PermissionDenied(
                "Senior Officers can only view their own department's queue."
            )

        return (
            Grievance.objects
            .filter(
                department_id=dept_pk,
                status=GrievanceStatus.SUBMITTED,
                assignment__isnull=True,
            )
            .order_by("created_at")
        )


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------

class AssignOfficerView(APIView):
    """
    POST /api/grievances/<pk>/assign/
    Body: { "officer_id": <int> }
    Senior Officer or Admin only.
    """
    permission_classes = [IsSeniorOfficerOrAdmin]

    def post(self, request, pk):
        grievance = get_object_or_404(Grievance, pk=pk)
        serializer = AssignOfficerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        officer = get_object_or_404(
            CustomUser, pk=serializer.validated_data["officer_id"]
        )

        from .services.assignment_service import assign_officer
        assign_officer(grievance, officer, assigned_by=request.user)

        return Response(
            GrievanceSerializer(grievance).data,
            status=status.HTTP_200_OK,
        )


class ReassignOfficerView(APIView):
    """
    POST /api/grievances/<pk>/reassign/
    Body: { "officer_id": <int>, "remarks": "..." }
    Senior Officer or Admin only. Records full assignment history.
    """
    permission_classes = [IsSeniorOfficerOrAdmin]

    def post(self, request, pk):
        grievance = get_object_or_404(Grievance, pk=pk)
        serializer = ReassignOfficerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        officer = get_object_or_404(
            CustomUser, pk=serializer.validated_data["officer_id"]
        )

        from .services.assignment_service import reassign_officer
        reassign_officer(
            grievance,
            officer,
            changed_by=request.user,
            remarks=serializer.validated_data.get("remarks", ""),
        )

        return Response(
            GrievanceSerializer(grievance).data,
            status=status.HTTP_200_OK,
        )


class AssignmentHistoryView(generics.ListAPIView):
    """
    GET /api/grievances/<pk>/assignment-history/
    Officer or Admin only.
    """
    serializer_class = AssignmentHistorySerializer
    permission_classes = [IsOfficer]

    def get_queryset(self):
        grievance = get_object_or_404(Grievance, pk=self.kwargs["pk"])
        return grievance.assignment_history.order_by("created_at")


# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

class UpdateStatusView(APIView):
    """
    POST /api/grievances/<pk>/status/
    Body: { "status": "<new_status>" }
    Any officer. Senior-only transitions validated inside the service.
    """
    permission_classes = [IsOfficer]

    def post(self, request, pk):
        grievance = get_object_or_404(Grievance, pk=pk)
        serializer = StatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .services.workflow_service import transition_status
        transition_status(
            grievance,
            serializer.validated_data["status"],
            changed_by=request.user,
        )

        return Response(
            GrievanceSerializer(grievance).data,
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Officer notes (internal — never exposed to citizens)
# ---------------------------------------------------------------------------

class OfficerNoteListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/grievances/<pk>/notes/
    POST /api/grievances/<pk>/notes/
    Officer only. Citizens never see these.
    """
    serializer_class = OfficerNoteSerializer
    permission_classes = [IsOfficer]

    def get_queryset(self):
        return OfficerNote.objects.filter(
            grievance_id=self.kwargs["pk"]
        ).order_by("created_at")

    def perform_create(self, serializer):
        grievance = get_object_or_404(Grievance, pk=self.kwargs["pk"])
        serializer.save(grievance=grievance, officer=self.request.user)


# ---------------------------------------------------------------------------
# Resolution evidence
# ---------------------------------------------------------------------------

class ResolutionEvidenceListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/grievances/<pk>/evidence/
    POST /api/grievances/<pk>/evidence/
    Officer only.
    """
    serializer_class = ResolutionEvidenceSerializer
    permission_classes = [IsOfficer]

    def get_queryset(self):
        return ResolutionEvidence.objects.filter(
            grievance_id=self.kwargs["pk"]
        ).order_by("uploaded_at")

    def perform_create(self, serializer):
        grievance = get_object_or_404(Grievance, pk=self.kwargs["pk"])
        serializer.save(grievance=grievance, uploaded_by=self.request.user)
