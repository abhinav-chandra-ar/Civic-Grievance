import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import CustomUser
from .enums import GrievanceStatus
from .models import Grievance, GrievanceTimelineEvent, Notification, OfficerNote, ReopenRequest, ResolutionEvidence
from .permissions import IsOfficer, IsOwnerOrAdmin, IsSeniorOfficerOrAdmin
from .serializers import (
    AssignmentHistorySerializer,
    AssignOfficerSerializer,
    GrievanceSerializer,
    GrievanceTimelineEventSerializer,
    NotificationSerializer,
    OfficerNoteSerializer,
    ReassignOfficerSerializer,
    ReopenRequestSerializer,
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
        from geolocation.models import GeolocationLog
        from geolocation.service import detect_ward

        # ------------------------------------------------------------------
        # Step 1 — Extract GPS coordinates from validated_data.
        # Pop them so they are not passed to Grievance.objects.create().
        # ------------------------------------------------------------------
        lat = serializer.validated_data.pop("latitude", None)
        lng = serializer.validated_data.pop("longitude", None)
        ward_from_body = serializer.validated_data.get("ward")

        # ------------------------------------------------------------------
        # Step 2 — GPS detection (only if coordinates were provided).
        # ------------------------------------------------------------------
        detected_ward    = None
        detection_method = None

        if lat is not None and lng is not None:
            detected_ward = detect_ward(lat, lng)
            detection_method = (
                GeolocationLog.DetectionMethod.GPS_AUTO
                if detected_ward
                else GeolocationLog.DetectionMethod.MANUAL_FALLBACK
            )

        # ------------------------------------------------------------------
        # Step 3 — Resolve final ward.
        # GPS takes priority; manual ward FK is the fallback.
        # ------------------------------------------------------------------
        if detected_ward:
            resolved_ward = detected_ward
        else:
            resolved_ward    = ward_from_body
            detection_method = GeolocationLog.DetectionMethod.MANUAL_FALLBACK

        # GPS was provided but landed outside all ward boundaries, and no
        # manual ward was supplied — reject so no unroutable grievance is saved.
        if resolved_ward is None:
            raise ValidationError(
                "GPS coordinates are outside all known ward boundaries. "
                "Please select your ward manually."
            )

        # ------------------------------------------------------------------
        # Step 4 — Save grievance with the resolved ward.
        # ------------------------------------------------------------------
        grievance = serializer.save(citizen=self.request.user, ward=resolved_ward)

        # ------------------------------------------------------------------
        # Step 5 — Write audit log (only when GPS coordinates were submitted).
        # ------------------------------------------------------------------
        if lat is not None:
            GeolocationLog.objects.create(
                grievance=grievance,
                submitted_lat=lat,
                submitted_lng=lng,
                detected_ward=detected_ward,
                detection_method=detection_method,
            )

        # ------------------------------------------------------------------
        # Step 6 — ML pipeline (unchanged).
        # ------------------------------------------------------------------
        try:
            from ml_engine.pipeline import run_ml_pipeline
            run_ml_pipeline(grievance)
        except Exception:
            logger.exception(
                "ML pipeline failed for grievance #%s -- grievance saved, ml_* fields blank",
                grievance.id,
            )

        # ------------------------------------------------------------------
        # Step 7 — Routing service (unchanged).
        # ------------------------------------------------------------------
        try:
            from routing.service import run_routing
            run_routing(grievance)
        except Exception:
            logger.exception(
                "Routing failed for grievance #%s -- department and jurisdiction not assigned",
                grievance.id,
            )

        # ------------------------------------------------------------------
        # Step 8 — Module 8: SUBMITTED timeline event + notification.
        # Non-fatal: timeline failure must not roll back the saved grievance.
        # ------------------------------------------------------------------
        try:
            from grievances.services.timeline_service import on_grievance_submitted
            on_grievance_submitted(grievance)
        except Exception:
            logger.exception(
                "Timeline/notification failed for grievance #%s -- grievance already saved",
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
        - Citizen: own grievance only.
        - Officer / Admin: any grievance.
    POST /api/grievances/<pk>/evidence/
        - Officer / Admin only.
    """
    serializer_class = ResolutionEvidenceSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsOfficer()]
        return [IsAuthenticated()]

    def get_queryset(self):
        grievance = get_object_or_404(Grievance, pk=self.kwargs["pk"])
        user = self.request.user

        # Citizens may only view evidence for their own grievance.
        if user.role not in ("JUNIOR_OFFICER", "SENIOR_OFFICER", "ADMIN"):
            if grievance.citizen != user:
                raise PermissionDenied(
                    "You can only view evidence for your own grievance."
                )

        return ResolutionEvidence.objects.filter(
            grievance=grievance
        ).order_by("uploaded_at")

    def perform_create(self, serializer):
        grievance = get_object_or_404(Grievance, pk=self.kwargs["pk"])
        serializer.save(grievance=grievance, uploaded_by=self.request.user)

        # Module 8: EVIDENCE_UPLOADED timeline event + citizen notification.
        from grievances.services.timeline_service import on_evidence_uploaded
        on_evidence_uploaded(grievance, self.request.user)


# ---------------------------------------------------------------------------
# Module 8 — Notifications
# ---------------------------------------------------------------------------

class NotificationListView(generics.ListAPIView):
    """
    GET /api/notifications/
    Returns the authenticated user's own notifications, newest first.
    Supports ?unread=true to filter unread only.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        if self.request.query_params.get("unread") == "true":
            qs = qs.filter(is_read=False)
        return qs.order_by("-created_at")


class NotificationReadView(APIView):
    """
    POST /api/notifications/{id}/read/
    Marks the notification as read.  Users may only update their own notifications.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)

        if notification.user != request.user:
            raise PermissionDenied("You can only mark your own notifications as read.")

        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Module 8 — Timeline
# ---------------------------------------------------------------------------

class GrievanceTimelineView(generics.ListAPIView):
    """
    GET /api/grievances/{id}/timeline/
    Returns the ordered lifecycle event log for a grievance.

    Citizen: own grievances only.
    Officer / Admin: any grievance accessible under existing rules.
    """
    serializer_class = GrievanceTimelineEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        grievance = get_object_or_404(Grievance, pk=self.kwargs["pk"])
        user = self.request.user

        if user.role not in ("JUNIOR_OFFICER", "SENIOR_OFFICER", "ADMIN"):
            if grievance.citizen != user:
                raise PermissionDenied(
                    "You can only view the timeline for your own grievances."
                )

        return GrievanceTimelineEvent.objects.filter(
            grievance=grievance
        ).order_by("created_at")


# ---------------------------------------------------------------------------
# Module 8 — Reopen
# ---------------------------------------------------------------------------

class ReopenGrievanceView(APIView):
    """
    POST /api/grievances/{id}/reopen/
    Body: { "reason": "...", "photo": <file> (optional) }

    Rules enforced:
      • Caller must be the grievance owner.
      • Grievance must currently be RESOLVED.
      • Request must arrive within settings.GRIEVANCE_REOPEN_WINDOW_DAYS
        (default 7) of resolution.

    On success:
      • ReopenRequest record created.
      • reopen_count incremented; last_reopened_at stamped.
      • transition_status(REOPENED) called — which triggers the existing
        workflow hook (on_status_changed) writing the REOPENED timeline event
        and citizen notification automatically.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        grievance = get_object_or_404(Grievance, pk=pk)

        # --- Ownership check ---
        if grievance.citizen != request.user:
            raise PermissionDenied("Only the grievance owner may request a reopen.")

        # --- Status check ---
        if grievance.status != GrievanceStatus.RESOLVED:
            raise ValidationError(
                {"detail": "Only resolved grievances can be reopened."}
            )

        # --- Reopen window check ---
        reopen_window_days = getattr(settings, "GRIEVANCE_REOPEN_WINDOW_DAYS", 7)
        # Use resolved_at when set (post-Phase 2 transitions); fall back to
        # updated_at for grievances resolved before the new field was added.
        reference_date = grievance.resolved_at or grievance.updated_at
        elapsed_days = (timezone.now() - reference_date).days
        if elapsed_days > reopen_window_days:
            raise ValidationError(
                {
                    "detail": (
                        f"The reopen window has expired. Grievances may only be "
                        f"reopened within {reopen_window_days} days of resolution."
                    )
                }
            )

        # --- Validate request body ---
        serializer = ReopenRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # --- Persist ReopenRequest ---
        serializer.save(grievance=grievance, requested_by=request.user)

        # --- Update reopen tracking counters ---
        grievance.reopen_count += 1
        grievance.last_reopened_at = timezone.now()
        grievance.save(update_fields=["reopen_count", "last_reopened_at"])

        # --- Transition status (RESOLVED → REOPENED).
        # transition_status validates the move, writes GrievanceStatusLog,
        # stamps last_status_change_at, and calls on_status_changed which
        # creates the REOPENED timeline event and citizen notification. ---
        from grievances.services.workflow_service import transition_status
        transition_status(grievance, GrievanceStatus.REOPENED, changed_by=request.user)

        return Response(GrievanceSerializer(grievance).data, status=status.HTTP_200_OK)
