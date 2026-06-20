from django.urls import path

from .views import (
    AssignmentHistoryView,
    AssignOfficerView,
    CreateGrievanceView,
    GrievanceDetailView,
    GrievanceTimelineView,
    MyGrievancesView,
    OfficerDashboardView,
    OfficerNoteListCreateView,
    ReassignOfficerView,
    ReopenGrievanceView,
    ResolutionEvidenceListCreateView,
    UpdateStatusView,
)

urlpatterns = [
    # Citizen
    path("", MyGrievancesView.as_view(), name="my-grievances"),
    path("create/", CreateGrievanceView.as_view(), name="create-grievance"),
    path("<int:pk>/", GrievanceDetailView.as_view(), name="grievance-detail"),

    # Workflow
    path("<int:pk>/assign/", AssignOfficerView.as_view(), name="grievance-assign"),
    path("<int:pk>/reassign/", ReassignOfficerView.as_view(), name="grievance-reassign"),
    path("<int:pk>/status/", UpdateStatusView.as_view(), name="grievance-status"),
    path("<int:pk>/assignment-history/", AssignmentHistoryView.as_view(), name="grievance-assignment-history"),

    # Officer notes & evidence
    path("<int:pk>/notes/", OfficerNoteListCreateView.as_view(), name="grievance-notes"),
    path("<int:pk>/evidence/", ResolutionEvidenceListCreateView.as_view(), name="grievance-evidence"),

    # Officer dashboard
    path("officer/", OfficerDashboardView.as_view(), name="officer-dashboard"),

    # Module 8 — Lifecycle visibility
    path("<int:pk>/timeline/", GrievanceTimelineView.as_view(), name="grievance-timeline"),
    path("<int:pk>/reopen/", ReopenGrievanceView.as_view(), name="grievance-reopen"),
]
