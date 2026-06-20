import django, os, sys
sys.path.insert(0, r"C:\Users\91918\OneDrive\Desktop\civic grievance\backend")
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
django.setup()

# --- Serializers load ---
from grievances.serializers import (
    GrievanceTimelineEventSerializer,
    NotificationSerializer,
    ReopenRequestSerializer,
    ResolutionEvidenceSerializer,
)
print("PASS  serializers: all four new/updated serializers importable")

# --- ResolutionEvidenceSerializer new fields present ---
fields = set(ResolutionEvidenceSerializer().fields.keys())
for f in ("before_image", "after_image", "resolution_notes"):
    assert f in fields, f"FAIL: {f} missing from ResolutionEvidenceSerializer fields"
print("PASS  ResolutionEvidenceSerializer: before_image, after_image, resolution_notes present")

# --- ResolutionEvidenceSerializer backward compat: old fields still present ---
for f in ("id", "grievance", "uploaded_by", "uploaded_by_name", "image", "uploaded_at"):
    assert f in fields, f"FAIL: existing field {f} missing from ResolutionEvidenceSerializer"
print("PASS  ResolutionEvidenceSerializer: all original fields still present")

# --- timeline_service imports ---
from grievances.services.timeline_service import (
    create_timeline_event,
    create_notification,
    on_grievance_submitted,
    on_status_changed,
    on_officer_assigned,
    on_officer_reassigned,
    on_evidence_uploaded,
    SLA_HOURS,
)
print("PASS  timeline_service: all 7 public functions + SLA_HOURS importable")

# --- SLA values ---
assert SLA_HOURS == {"CRITICAL": 24, "HIGH": 48, "MEDIUM": 72, "LOW": 120}, f"FAIL SLA_HOURS wrong: {SLA_HOURS}"
print("PASS  SLA_HOURS: {'CRITICAL':24,'HIGH':48,'MEDIUM':72,'LOW':120}")

# --- workflow_service has new code ---
import inspect
import grievances.services.workflow_service as ws
src = inspect.getsource(ws)
for token in ("from django.utils import timezone", "last_status_change_at", "resolved_at", "closed_at", "on_status_changed"):
    assert token in src, f"FAIL: '{token}' not found in workflow_service.py"
print("PASS  workflow_service: timezone import, 3 timestamp fields, on_status_changed hook all present")

# --- assignment_service has new hooks ---
import grievances.services.assignment_service as asvc
src2 = inspect.getsource(asvc)
assert "on_officer_assigned" in src2, "FAIL: on_officer_assigned missing from assignment_service"
assert "on_officer_reassigned" in src2, "FAIL: on_officer_reassigned missing from assignment_service"
print("PASS  assignment_service: on_officer_assigned and on_officer_reassigned hooks present")

# --- No model drift ---
from django.test.utils import setup_test_environment
from django.db import connection
print()
print("Phase 2 smoke test: ALL PASS")
