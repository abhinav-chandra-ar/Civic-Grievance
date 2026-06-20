"""
Phase 3 functional smoke test.
Uses Django test client with in-process requests — no live server needed.
Creates minimal fixture data to exercise every new endpoint.
"""
import os, sys, django
sys.path.insert(0, r"C:\Users\91918\OneDrive\Desktop\civic grievance\backend")
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from grievances.models import (
    Grievance, GrievanceTimelineEvent, Notification, ReopenRequest,
)
from grievances.enums import GrievanceStatus
from grievances.views import (
    NotificationListView, NotificationReadView,
    GrievanceTimelineView, ReopenGrievanceView,
    ResolutionEvidenceListCreateView,
)
from routing.models import Ward, Jurisdiction
from departments.models import Department

User = get_user_model()
factory = APIRequestFactory()

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------
def get_or_create_dept():
    return Department.objects.first() or Department.objects.create(name="KWA", code="KWA")

def get_or_create_ward():
    return Ward.objects.filter(boundary__isnull=False).first() or Ward.objects.first()

def get_or_create_citizen(suffix=""):
    email = f"test_citizen{suffix}@example.com"
    u, _ = User.objects.get_or_create(email=email, defaults={"full_name": f"Test Citizen{suffix}", "role": "CITIZEN"})
    u.set_password("pass")
    u.save()
    return u

def get_or_create_officer():
    dept = get_or_create_dept()
    email = "test_officer@example.com"
    u, _ = User.objects.get_or_create(email=email, defaults={"full_name": "Test Officer", "role": "JUNIOR_OFFICER", "department": dept})
    u.set_password("pass")
    u.save()
    return u

def make_grievance(citizen, status_val=GrievanceStatus.SUBMITTED):
    ward = get_or_create_ward()
    dept = get_or_create_dept()
    g = Grievance.objects.create(
        citizen=citizen,
        ward=ward,
        department=dept,
        raw_text="Test grievance description that is long enough.",
        status=status_val,
    )
    return g

PASS_COUNT = 0
FAIL_COUNT = 0

def check(label, condition, detail=""):
    global PASS_COUNT, FAIL_COUNT
    if condition:
        print(f"  PASS  {label}")
        PASS_COUNT += 1
    else:
        print(f"  FAIL  {label}" + (f" — {detail}" if detail else ""))
        FAIL_COUNT += 1

# ---------------------------------------------------------------------------
# Test: NotificationListView
# ---------------------------------------------------------------------------
print("\n[1] NotificationListView GET /api/notifications/")
citizen = get_or_create_citizen()
other   = get_or_create_citizen("_other")

notif = Notification.objects.create(
    user=citizen,
    notification_type="GRIEVANCE_SUBMITTED",
    title="Test",
    message="Test message",
)
Notification.objects.create(
    user=other,
    notification_type="GRIEVANCE_SUBMITTED",
    title="Other",
    message="Should not appear",
)

req = factory.get("/api/notifications/")
force_authenticate(req, user=citizen)
resp = NotificationListView.as_view()(req)
check("Status 200", resp.status_code == 200, str(resp.status_code))
ids = [n["id"] for n in resp.data["results"]]
check("Returns own notification", notif.id in ids)
# Confirm other user's notification is absent (list is scoped to request.user)
all_ids = [n["id"] for n in resp.data["results"]]
other_notifs = list(Notification.objects.filter(user=other).values_list("id", flat=True))
check("Does not return other user's notifications",
      not any(oid in all_ids for oid in other_notifs))

# unread filter
req2 = factory.get("/api/notifications/", {"unread": "true"})
force_authenticate(req2, user=citizen)
resp2 = NotificationListView.as_view()(req2)
check("?unread=true filter works", resp2.status_code == 200)

# ---------------------------------------------------------------------------
# Test: NotificationReadView
# ---------------------------------------------------------------------------
print("\n[2] NotificationReadView POST /api/notifications/{id}/read/")
req = factory.post(f"/api/notifications/{notif.id}/read/")
force_authenticate(req, user=citizen)
resp = NotificationReadView.as_view()(req, pk=notif.id)
check("Status 200", resp.status_code == 200, str(resp.status_code))
check("is_read=True in response", resp.data.get("is_read") is True)
notif.refresh_from_db()
check("is_read=True persisted in DB", notif.is_read is True)

# Cannot mark other user's notification
other_notif = Notification.objects.filter(user=other).first()
if other_notif:
    req = factory.post(f"/api/notifications/{other_notif.id}/read/")
    force_authenticate(req, user=citizen)
    resp = NotificationReadView.as_view()(req, pk=other_notif.id)
    check("Cannot mark another user's notification (403)", resp.status_code == 403)

# ---------------------------------------------------------------------------
# Test: GrievanceTimelineView
# ---------------------------------------------------------------------------
print("\n[3] GrievanceTimelineView GET /api/grievances/{id}/timeline/")
g = make_grievance(citizen)
GrievanceTimelineEvent.objects.create(
    grievance=g,
    event_type="SUBMITTED",
    description="Grievance submitted.",
    created_by=citizen,
)

# Citizen can view own
req = factory.get(f"/api/grievances/{g.id}/timeline/")
force_authenticate(req, user=citizen)
resp = GrievanceTimelineView.as_view()(req, pk=g.id)
check("Citizen: status 200 for own grievance", resp.status_code == 200, str(resp.status_code))
check("Returns at least 1 timeline event", len(resp.data) >= 1 or len(resp.data.get("results", [])) >= 1)

# Citizen cannot view other's grievance timeline
other_grievance = make_grievance(other)
req = factory.get(f"/api/grievances/{other_grievance.id}/timeline/")
force_authenticate(req, user=citizen)
resp = GrievanceTimelineView.as_view()(req, pk=other_grievance.id)
check("Citizen: 403 for another citizen's grievance timeline", resp.status_code == 403)

# Officer can view any
officer = get_or_create_officer()
req = factory.get(f"/api/grievances/{other_grievance.id}/timeline/")
force_authenticate(req, user=officer)
resp = GrievanceTimelineView.as_view()(req, pk=other_grievance.id)
check("Officer: 200 for any grievance timeline", resp.status_code == 200, str(resp.status_code))

# ---------------------------------------------------------------------------
# Test: ReopenGrievanceView
# ---------------------------------------------------------------------------
print("\n[4] ReopenGrievanceView POST /api/grievances/{id}/reopen/")

# Create a RESOLVED grievance with resolved_at set
resolved_g = make_grievance(citizen, status_val=GrievanceStatus.RESOLVED)
resolved_g.resolved_at = timezone.now()
resolved_g.save(update_fields=["resolved_at"])

# Valid reopen
req = factory.post(f"/api/grievances/{resolved_g.id}/reopen/",
                   {"reason": "The issue is not fixed yet."}, format="json")
force_authenticate(req, user=citizen)
resp = ReopenGrievanceView.as_view()(req, pk=resolved_g.id)
check("Valid reopen: status 200", resp.status_code == 200, str(resp.status_code))
resolved_g.refresh_from_db()
check("Status changed to REOPENED", resolved_g.status == GrievanceStatus.REOPENED)
check("reopen_count incremented to 1", resolved_g.reopen_count == 1)
check("last_reopened_at set", resolved_g.last_reopened_at is not None)
check("ReopenRequest record created",
      ReopenRequest.objects.filter(grievance=resolved_g).exists())
check("REOPENED timeline event created",
      GrievanceTimelineEvent.objects.filter(grievance=resolved_g, event_type="REOPENED").exists())
check("REOPENED citizen notification created",
      Notification.objects.filter(grievance=resolved_g, notification_type="REOPENED").exists())

# Cannot reopen a non-RESOLVED grievance
submitted_g = make_grievance(citizen, status_val=GrievanceStatus.SUBMITTED)
req = factory.post(f"/api/grievances/{submitted_g.id}/reopen/",
                   {"reason": "Wrong status test."}, format="json")
force_authenticate(req, user=citizen)
resp = ReopenGrievanceView.as_view()(req, pk=submitted_g.id)
check("Reopen non-RESOLVED -> 400", resp.status_code == 400, str(resp.status_code))

# Cannot reopen another citizen's grievance
other_resolved = make_grievance(other, status_val=GrievanceStatus.RESOLVED)
other_resolved.resolved_at = timezone.now()
other_resolved.save(update_fields=["resolved_at"])
req = factory.post(f"/api/grievances/{other_resolved.id}/reopen/",
                   {"reason": "Trying to reopen other's grievance."}, format="json")
force_authenticate(req, user=citizen)
resp = ReopenGrievanceView.as_view()(req, pk=other_resolved.id)
check("Cannot reopen another citizen's grievance -> 403", resp.status_code == 403)

# Expired reopen window
old_resolved = make_grievance(citizen, status_val=GrievanceStatus.RESOLVED)
from datetime import timedelta
old_resolved.resolved_at = timezone.now() - timedelta(days=10)
old_resolved.save(update_fields=["resolved_at"])
req = factory.post(f"/api/grievances/{old_resolved.id}/reopen/",
                   {"reason": "Expired window test."}, format="json")
force_authenticate(req, user=citizen)
resp = ReopenGrievanceView.as_view()(req, pk=old_resolved.id)
check("Expired reopen window -> 400", resp.status_code == 400, str(resp.status_code))

# ---------------------------------------------------------------------------
# Test: on_grievance_submitted hook (SUBMITTED event via perform_create)
# ---------------------------------------------------------------------------
print("\n[5] on_grievance_submitted integration")
g2 = make_grievance(citizen)
from grievances.services.timeline_service import on_grievance_submitted
on_grievance_submitted(g2)
check("SUBMITTED timeline event written",
      GrievanceTimelineEvent.objects.filter(grievance=g2, event_type="SUBMITTED").exists())
check("GRIEVANCE_SUBMITTED notification written",
      Notification.objects.filter(grievance=g2, notification_type="GRIEVANCE_SUBMITTED").exists())

# ---------------------------------------------------------------------------
# Test: ResolutionEvidence citizen GET
# ---------------------------------------------------------------------------
print("\n[6] ResolutionEvidenceListCreateView citizen GET")
from grievances.models import ResolutionEvidence
# Citizen can view own evidence
req = factory.get(f"/api/grievances/{g.id}/evidence/")
force_authenticate(req, user=citizen)
resp = ResolutionEvidenceListCreateView.as_view()(req, pk=g.id)
check("Citizen: 200 for own grievance evidence", resp.status_code == 200, str(resp.status_code))

# Citizen cannot view another's evidence
req = factory.get(f"/api/grievances/{other_grievance.id}/evidence/")
force_authenticate(req, user=citizen)
resp = ResolutionEvidenceListCreateView.as_view()(req, pk=other_grievance.id)
check("Citizen: 403 for another's evidence", resp.status_code == 403, str(resp.status_code))

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print(f"\n{'='*60}")
print(f"Phase 3 smoke test: {PASS_COUNT} PASS  {FAIL_COUNT} FAIL")
if FAIL_COUNT > 0:
    print("REVIEW FAILURES ABOVE")
else:
    print("ALL PASS")
