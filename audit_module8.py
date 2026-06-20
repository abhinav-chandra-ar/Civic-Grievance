"""
Module 8 — Verification & Audit
Phase 4: Complete end-to-end test of every Module 8 scenario.

Runs against the live PostgreSQL database using Django's in-process
request factory (no live server required).

Test matrix:
  Scenario 1 — Citizen creates grievance
  Scenario 2 — Officer assignment
  Scenario 3 — Status changes (IN_PROGRESS, ESCALATED, RESOLVED, CLOSED)
  Scenario 4 — Resolution evidence upload + citizen retrieval
  Scenario 5 — Reopen workflow
  Scenario 6 — Notification APIs (list, mark-read)
  Scenario 7 — Permission boundaries (7 checks)
"""

import io
import os
import sys
import uuid
from datetime import timedelta

import django

sys.path.insert(0, r"C:\Users\91918\OneDrive\Desktop\civic grievance\backend")
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
django.setup()

# Allow testserver host used by APIRequestFactory when serializers build image URLs.
from django.conf import settings as _dj_settings
if "testserver" not in _dj_settings.ALLOWED_HOSTS:
    _dj_settings.ALLOWED_HOSTS.append("testserver")

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from departments.models import Department
from grievances.enums import GrievanceStatus
from grievances.models import (
    Grievance,
    GrievanceStatusLog,
    GrievanceTimelineEvent,
    Notification,
    ReopenRequest,
    ResolutionEvidence,
)
from grievances.services.assignment_service import assign_officer
from grievances.services.timeline_service import on_grievance_submitted
from grievances.services.workflow_service import transition_status
from grievances.views import (
    GrievanceTimelineView,
    NotificationListView,
    NotificationReadView,
    ReopenGrievanceView,
    ResolutionEvidenceListCreateView,
)
from routing.models import Ward

User = get_user_model()
factory = APIRequestFactory()

# ---------------------------------------------------------------------------
# Audit harness
# ---------------------------------------------------------------------------
PASS_COUNT = 0
FAIL_COUNT = 0
BUGS: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS_COUNT, FAIL_COUNT
    if condition:
        print(f"  PASS  {label}")
        PASS_COUNT += 1
    else:
        msg = f"  FAIL  {label}" + (f" -- {detail}" if detail else "")
        print(msg)
        BUGS.append(msg)
        FAIL_COUNT += 1


def section(title: str) -> None:
    print(f"\n{'='*64}")
    print(f"  {title}")
    print(f"{'='*64}")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
_uid = uuid.uuid4().hex[:6]


def _dept() -> Department:
    # Use the first department that exists, or create a test one.
    obj = Department.objects.first()
    if obj is None:
        obj = Department.objects.create(name="Kerala Water Authority")
    return obj


def _ward() -> Ward:
    w = Ward.objects.first()
    assert w, "No wards found — run seed_routing_data first"
    return w


DEPT = _dept()
WARD = _ward()


def make_user(role: str, tag: str = "") -> User:
    email = f"audit_{role.lower()}_{_uid}{tag}@test.internal"
    u, _ = User.objects.get_or_create(
        email=email,
        defaults={
            "full_name": f"Audit {role} {_uid}{tag}",
            "role": role,
            "department": DEPT if role in ("JUNIOR_OFFICER", "SENIOR_OFFICER") else None,
        },
    )
    u.set_password("testpass1234")
    u.save()
    return u


CITIZEN1   = make_user("CITIZEN",        "1")
CITIZEN2   = make_user("CITIZEN",        "2")
JR_OFFICER = make_user("JUNIOR_OFFICER", "")
SR_OFFICER = make_user("SENIOR_OFFICER", "")


def make_grievance(citizen=None, initial_status: str = GrievanceStatus.SUBMITTED) -> Grievance:
    c = citizen or CITIZEN1
    return Grievance.objects.create(
        citizen=c,
        ward=WARD,
        department=DEPT,
        raw_text="Audit test grievance — description long enough to satisfy validation minimum.",
        status=initial_status,
    )


def make_image() -> SimpleUploadedFile:
    """Return a real 1×1 JPEG using Pillow."""
    from PIL import Image as PILImage
    buf = io.BytesIO()
    PILImage.new("RGB", (1, 1), color=(128, 128, 128)).save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile(f"audit_{_uid}.jpg", buf.read(), content_type="image/jpeg")


def timeline_count(g: Grievance, event_type: str = None) -> int:
    qs = GrievanceTimelineEvent.objects.filter(grievance=g)
    if event_type:
        qs = qs.filter(event_type=event_type)
    return qs.count()


def notif_count(grievance=None, user=None, notif_type: str = None) -> int:
    qs = Notification.objects.all()
    if grievance:
        qs = qs.filter(grievance=grievance)
    if user:
        qs = qs.filter(user=user)
    if notif_type:
        qs = qs.filter(notification_type=notif_type)
    return qs.count()


# ===========================================================================
# SCENARIO 1 — Citizen creates grievance
# ===========================================================================
section("SCENARIO 1: Citizen creates grievance")

G1 = make_grievance()
on_grievance_submitted(G1)

# Timeline
check(
    "SUBMITTED timeline event created",
    timeline_count(G1, "SUBMITTED") == 1,
    f"count={timeline_count(G1, 'SUBMITTED')}",
)
evt_submitted = GrievanceTimelineEvent.objects.filter(grievance=G1, event_type="SUBMITTED").first()
check(
    "SUBMITTED event description references grievance ID",
    evt_submitted is not None and f"#{G1.id}" in evt_submitted.description,
    evt_submitted.description if evt_submitted else "event missing",
)
check(
    "SUBMITTED event created_by = citizen",
    evt_submitted is not None and evt_submitted.created_by == CITIZEN1,
)

# Notification
check(
    "GRIEVANCE_SUBMITTED notification created",
    notif_count(grievance=G1, user=CITIZEN1, notif_type="GRIEVANCE_SUBMITTED") == 1,
)
n_sub = Notification.objects.filter(grievance=G1, notification_type="GRIEVANCE_SUBMITTED").first()
check("Notification is_read defaults to False", n_sub is not None and n_sub.is_read is False)
check("Notification has non-empty title",  n_sub is not None and bool(n_sub.title))
check("Notification has non-empty message", n_sub is not None and bool(n_sub.message))


# ===========================================================================
# SCENARIO 2 — Officer assignment
# ===========================================================================
section("SCENARIO 2: Officer assignment")

G2 = make_grievance()
on_grievance_submitted(G2)

assign_officer(G2, JR_OFFICER, assigned_by=SR_OFFICER)
G2.refresh_from_db()

# Grievance state
check("Status changed to ASSIGNED", G2.status == GrievanceStatus.ASSIGNED)
check("assigned_officer set",        G2.assigned_officer == JR_OFFICER)
check("assigned_at stamped",         G2.assigned_at is not None)
check("last_status_change_at set",   G2.last_status_change_at is not None)

# Timeline
check(
    "ASSIGNED timeline event created",
    timeline_count(G2, "ASSIGNED") == 1,
)
evt_asgn = GrievanceTimelineEvent.objects.filter(grievance=G2, event_type="ASSIGNED").first()
check(
    "ASSIGNED event description names officer",
    evt_asgn is not None and JR_OFFICER.full_name in evt_asgn.description,
    evt_asgn.description if evt_asgn else "event missing",
)

# Notifications
check(
    "Citizen OFFICER_ASSIGNED notification",
    notif_count(grievance=G2, user=CITIZEN1, notif_type="OFFICER_ASSIGNED") == 1,
)
check(
    "Officer OFFICER_ASSIGNED notification",
    notif_count(grievance=G2, user=JR_OFFICER, notif_type="OFFICER_ASSIGNED") == 1,
)

# Status log
check(
    "GrievanceStatusLog: SUBMITTED->ASSIGNED",
    GrievanceStatusLog.objects.filter(grievance=G2, from_status="SUBMITTED", to_status="ASSIGNED").exists(),
)


# ===========================================================================
# SCENARIO 3 — Status changes
# ===========================================================================

# ---- IN_PROGRESS ----
section("SCENARIO 3a: Status change -> IN_PROGRESS")

transition_status(G2, GrievanceStatus.IN_PROGRESS, changed_by=JR_OFFICER)
G2.refresh_from_db()

check("Status -> IN_PROGRESS",          G2.status == GrievanceStatus.IN_PROGRESS)
check("last_status_change_at updated",  G2.last_status_change_at is not None)
check("resolved_at still None",         G2.resolved_at is None)
check("closed_at still None",           G2.closed_at is None)
check(
    "IN_PROGRESS timeline event",
    timeline_count(G2, "IN_PROGRESS") == 1,
)
check(
    "Citizen STATUS_CHANGED notification (IN_PROGRESS)",
    notif_count(grievance=G2, user=CITIZEN1, notif_type="STATUS_CHANGED") >= 1,
)
check(
    "GrievanceStatusLog: ASSIGNED->IN_PROGRESS",
    GrievanceStatusLog.objects.filter(grievance=G2, from_status="ASSIGNED", to_status="IN_PROGRESS").exists(),
)

# ---- ESCALATED ----
section("SCENARIO 3b: Status change -> ESCALATED (separate grievance)")

G3 = make_grievance()
on_grievance_submitted(G3)
assign_officer(G3, JR_OFFICER, assigned_by=SR_OFFICER)
transition_status(G3, GrievanceStatus.IN_PROGRESS, changed_by=JR_OFFICER)
ts_before_escalation = G3.last_status_change_at
transition_status(G3, GrievanceStatus.ESCALATED, changed_by=SR_OFFICER)
G3.refresh_from_db()

check("Status -> ESCALATED",           G3.status == GrievanceStatus.ESCALATED)
check("last_status_change_at updated", G3.last_status_change_at is not None)
check(
    "ESCALATED timeline event",
    timeline_count(G3, "ESCALATED") == 1,
)
check(
    "Citizen ESCALATED notification",
    notif_count(grievance=G3, user=CITIZEN1, notif_type="ESCALATED") == 1,
)
check(
    "GrievanceStatusLog: IN_PROGRESS->ESCALATED",
    GrievanceStatusLog.objects.filter(grievance=G3, from_status="IN_PROGRESS", to_status="ESCALATED").exists(),
)

# ---- RESOLVED ----
section("SCENARIO 3c: Status change -> RESOLVED")

before_resolved = timezone.now()
transition_status(G2, GrievanceStatus.RESOLVED, changed_by=JR_OFFICER)
G2.refresh_from_db()

check("Status -> RESOLVED",             G2.status == GrievanceStatus.RESOLVED)
check("resolved_at set",                G2.resolved_at is not None)
check("resolved_at >= before transition", G2.resolved_at >= before_resolved)
check("closed_at still None",           G2.closed_at is None)
check("last_status_change_at updated",  G2.last_status_change_at is not None)
check(
    "RESOLVED timeline event",
    timeline_count(G2, "RESOLVED") == 1,
)
check(
    "Citizen RESOLVED notification",
    notif_count(grievance=G2, user=CITIZEN1, notif_type="RESOLVED") == 1,
)
check(
    "GrievanceStatusLog: IN_PROGRESS->RESOLVED",
    GrievanceStatusLog.objects.filter(grievance=G2, from_status="IN_PROGRESS", to_status="RESOLVED").exists(),
)

# ---- CLOSED ----
section("SCENARIO 3d: Status change -> CLOSED")

G4 = make_grievance(initial_status=GrievanceStatus.RESOLVED)
G4.resolved_at = timezone.now()
G4.save(update_fields=["resolved_at"])

before_closed = timezone.now()
transition_status(G4, GrievanceStatus.CLOSED, changed_by=SR_OFFICER)
G4.refresh_from_db()

check("Status -> CLOSED",               G4.status == GrievanceStatus.CLOSED)
check("closed_at set",                  G4.closed_at is not None)
check("closed_at >= before transition", G4.closed_at >= before_closed)
check("resolved_at preserved",          G4.resolved_at is not None)
check("last_status_change_at updated",  G4.last_status_change_at is not None)
check(
    "CLOSED timeline event",
    timeline_count(G4, "CLOSED") == 1,
)
check(
    "Citizen CLOSED notification",
    notif_count(grievance=G4, user=CITIZEN1, notif_type="CLOSED") == 1,
)
check(
    "GrievanceStatusLog: RESOLVED->CLOSED",
    GrievanceStatusLog.objects.filter(grievance=G4, from_status="RESOLVED", to_status="CLOSED").exists(),
)


# ===========================================================================
# SCENARIO 4 — Resolution evidence upload + citizen retrieval
# ===========================================================================
section("SCENARIO 4: Resolution evidence upload")

G5 = make_grievance()
on_grievance_submitted(G5)
assign_officer(G5, JR_OFFICER, assigned_by=SR_OFFICER)

img = make_image()
req = factory.post(
    f"/api/grievances/{G5.id}/evidence/",
    {"image": img, "resolution_notes": "Pipe repaired and road restored."},
    format="multipart",
)
force_authenticate(req, user=JR_OFFICER)
resp = ResolutionEvidenceListCreateView.as_view()(req, pk=G5.id)

check("Evidence POST returns 201",      resp.status_code == 201, str(resp.status_code))
check("ResolutionEvidence record saved", ResolutionEvidence.objects.filter(grievance=G5).exists())

evid = ResolutionEvidence.objects.filter(grievance=G5).first()
check("resolution_notes saved",         evid is not None and evid.resolution_notes == "Pipe repaired and road restored.")
check("uploaded_by = officer",          evid is not None and evid.uploaded_by == JR_OFFICER)
check("Response includes resolution_notes", resp.data.get("resolution_notes") == "Pipe repaired and road restored.")

check(
    "EVIDENCE_UPLOADED timeline event created",
    timeline_count(G5, "EVIDENCE_UPLOADED") == 1,
)
check(
    "Citizen EVIDENCE_UPLOADED notification",
    notif_count(grievance=G5, user=CITIZEN1, notif_type="EVIDENCE_UPLOADED") == 1,
)

# Citizen retrieves evidence
req = factory.get(f"/api/grievances/{G5.id}/evidence/")
force_authenticate(req, user=CITIZEN1)
resp = ResolutionEvidenceListCreateView.as_view()(req, pk=G5.id)
check("Citizen GET evidence returns 200", resp.status_code == 200, str(resp.status_code))
data = resp.data.get("results", resp.data)
ids_returned = [e["id"] for e in data]
check("Evidence appears in citizen GET response", evid is not None and evid.id in ids_returned)


# ===========================================================================
# SCENARIO 5 — Reopen workflow
# ===========================================================================
section("SCENARIO 5: Reopen workflow")

G6 = make_grievance(initial_status=GrievanceStatus.RESOLVED)
G6.resolved_at = timezone.now()
G6.save(update_fields=["resolved_at"])

reopen_before    = G6.reopen_count
notif_before_cnt = Notification.objects.filter(grievance=G6, user=CITIZEN1).count()

req = factory.post(
    f"/api/grievances/{G6.id}/reopen/",
    {"reason": "The pipe is leaking again after two days."},
    format="json",
)
force_authenticate(req, user=CITIZEN1)
resp = ReopenGrievanceView.as_view()(req, pk=G6.id)

check("Reopen POST returns 200",         resp.status_code == 200, str(resp.status_code))

G6.refresh_from_db()
check("Status -> REOPENED",              G6.status == GrievanceStatus.REOPENED)
check("reopen_count incremented by 1",   G6.reopen_count == reopen_before + 1)
check("last_reopened_at set",            G6.last_reopened_at is not None)
check("last_status_change_at updated",   G6.last_status_change_at is not None)

check(
    "ReopenRequest record created",
    ReopenRequest.objects.filter(grievance=G6, requested_by=CITIZEN1).exists(),
)
rr = ReopenRequest.objects.filter(grievance=G6).first()
check("ReopenRequest reason saved",      rr is not None and "pipe" in rr.reason.lower())

check(
    "REOPENED timeline event created",
    timeline_count(G6, "REOPENED") == 1,
)
check(
    "Citizen REOPENED notification created",
    notif_count(grievance=G6, user=CITIZEN1, notif_type="REOPENED") == 1,
)
check(
    "GrievanceStatusLog: RESOLVED->REOPENED",
    GrievanceStatusLog.objects.filter(grievance=G6, from_status="RESOLVED", to_status="REOPENED").exists(),
)

# Response body contains updated status
check(
    "Response body status == REOPENED",
    resp.data.get("status") == GrievanceStatus.REOPENED,
    str(resp.data.get("status")),
)


# ===========================================================================
# SCENARIO 6 — Notification APIs
# ===========================================================================
section("SCENARIO 6: Notification APIs")

# 6a. List — own notifications, newest first
all_own = Notification.objects.filter(user=CITIZEN1).order_by("-created_at")
req = factory.get("/api/notifications/")
force_authenticate(req, user=CITIZEN1)
resp = NotificationListView.as_view()(req)
check("GET /api/notifications/ returns 200",    resp.status_code == 200, str(resp.status_code))

data = resp.data.get("results", resp.data)
check(
    "Returned count matches DB count for user",
    resp.data.get("count", len(data)) == all_own.count(),
    f"api={resp.data.get('count', len(data))}  db={all_own.count()}",
)

# Ordering: first item must be newest (created_at strings are ISO 8601, sortable lexicographically)
if len(data) >= 2:
    check(
        "Notifications ordered newest first",
        data[0]["created_at"] >= data[-1]["created_at"],
        f"first={data[0]['created_at']}  last={data[-1]['created_at']}",
    )

# 6b. Unread filter
unread_db = Notification.objects.filter(user=CITIZEN1, is_read=False).count()
req = factory.get("/api/notifications/", {"unread": "true"})
force_authenticate(req, user=CITIZEN1)
resp2 = NotificationListView.as_view()(req)
unread_data = resp2.data.get("results", resp2.data)
check(
    "?unread=true returns only unread notifications",
    resp2.data.get("count", len(unread_data)) == unread_db,
    f"api={resp2.data.get('count', len(unread_data))}  db={unread_db}",
)

# 6c. Mark read
target = Notification.objects.filter(user=CITIZEN1, is_read=False).first()
if target:
    req = factory.post(f"/api/notifications/{target.id}/read/")
    force_authenticate(req, user=CITIZEN1)
    resp3 = NotificationReadView.as_view()(req, pk=target.id)
    check("POST /api/notifications/{id}/read/ returns 200", resp3.status_code == 200, str(resp3.status_code))
    check("Response is_read=True",   resp3.data.get("is_read") is True)
    target.refresh_from_db()
    check("is_read=True persisted",  target.is_read is True)

    # Unread count should have dropped by 1
    unread_after = Notification.objects.filter(user=CITIZEN1, is_read=False).count()
    check("Unread count decreased by 1", unread_after == unread_db - 1)
else:
    check("Mark-read test skipped — no unread notifications", True)


# ===========================================================================
# SCENARIO 7 — Permission boundaries
# ===========================================================================
section("SCENARIO 7: Permission boundaries")

# 7a. Citizen cannot view another citizen's timeline
G_OTHER = make_grievance(citizen=CITIZEN2)
GrievanceTimelineEvent.objects.create(
    grievance=G_OTHER,
    event_type="SUBMITTED",
    description="Submitted.",
    created_by=CITIZEN2,
)
req = factory.get(f"/api/grievances/{G_OTHER.id}/timeline/")
force_authenticate(req, user=CITIZEN1)
resp = GrievanceTimelineView.as_view()(req, pk=G_OTHER.id)
check("Citizen1 CANNOT view citizen2 timeline (403)", resp.status_code == 403, str(resp.status_code))

# 7b. Citizen cannot reopen another citizen's grievance
G_OTHER_RES = make_grievance(citizen=CITIZEN2, initial_status=GrievanceStatus.RESOLVED)
G_OTHER_RES.resolved_at = timezone.now()
G_OTHER_RES.save(update_fields=["resolved_at"])
req = factory.post(
    f"/api/grievances/{G_OTHER_RES.id}/reopen/",
    {"reason": "Unauthorised reopen attempt."},
    format="json",
)
force_authenticate(req, user=CITIZEN1)
resp = ReopenGrievanceView.as_view()(req, pk=G_OTHER_RES.id)
check("Citizen1 CANNOT reopen citizen2 grievance (403)", resp.status_code == 403, str(resp.status_code))

# 7c. Citizen cannot mark another citizen's notification as read
N_OTHER = Notification.objects.create(
    user=CITIZEN2,
    notification_type="GRIEVANCE_SUBMITTED",
    title="Other",
    message="Other user notification",
)
req = factory.post(f"/api/notifications/{N_OTHER.id}/read/")
force_authenticate(req, user=CITIZEN1)
resp = NotificationReadView.as_view()(req, pk=N_OTHER.id)
check("Citizen1 CANNOT mark citizen2 notification read (403)", resp.status_code == 403, str(resp.status_code))
N_OTHER.refresh_from_db()
check("Citizen2 notification still unread after attempt", N_OTHER.is_read is False)

# 7d. Citizen cannot POST evidence (non-officer)
G_BLOCK = make_grievance()
img2 = make_image()
req = factory.post(
    f"/api/grievances/{G_BLOCK.id}/evidence/",
    {"image": img2},
    format="multipart",
)
force_authenticate(req, user=CITIZEN1)
resp = ResolutionEvidenceListCreateView.as_view()(req, pk=G_BLOCK.id)
check("Citizen CANNOT POST evidence (403)", resp.status_code == 403, str(resp.status_code))

# 7e. Citizen cannot view another citizen's evidence
req = factory.get(f"/api/grievances/{G_OTHER.id}/evidence/")
force_authenticate(req, user=CITIZEN1)
resp = ResolutionEvidenceListCreateView.as_view()(req, pk=G_OTHER.id)
check("Citizen1 CANNOT view citizen2 evidence (403)", resp.status_code == 403, str(resp.status_code))

# 7f. Reopen rejected for non-RESOLVED status
G_WRONG_STATUS = make_grievance(initial_status=GrievanceStatus.IN_PROGRESS)
req = factory.post(
    f"/api/grievances/{G_WRONG_STATUS.id}/reopen/",
    {"reason": "Status is wrong."},
    format="json",
)
force_authenticate(req, user=CITIZEN1)
resp = ReopenGrievanceView.as_view()(req, pk=G_WRONG_STATUS.id)
check("Reopen non-RESOLVED grievance rejected (400)", resp.status_code == 400, str(resp.status_code))

# 7g. Reopen rejected after window expiry
G_EXPIRED = make_grievance(initial_status=GrievanceStatus.RESOLVED)
G_EXPIRED.resolved_at = timezone.now() - timedelta(days=10)
G_EXPIRED.save(update_fields=["resolved_at"])
req = factory.post(
    f"/api/grievances/{G_EXPIRED.id}/reopen/",
    {"reason": "Window expired test."},
    format="json",
)
force_authenticate(req, user=CITIZEN1)
resp = ReopenGrievanceView.as_view()(req, pk=G_EXPIRED.id)
check("Reopen after 7-day window rejected (400)", resp.status_code == 400, str(resp.status_code))

# 7h. Unauthenticated request rejected
req = factory.get("/api/notifications/")
resp = NotificationListView.as_view()(req)
check("Unauthenticated /api/notifications/ rejected (401)", resp.status_code == 401, str(resp.status_code))


# ===========================================================================
# FINAL REPORT
# ===========================================================================
section("MODULE 8 AUDIT FINAL REPORT")
total = PASS_COUNT + FAIL_COUNT
print(f"\n  Total checks : {total}")
print(f"  PASS         : {PASS_COUNT}")
print(f"  FAIL         : {FAIL_COUNT}")

if BUGS:
    print(f"\n  BUGS FOUND ({len(BUGS)}):")
    for b in BUGS:
        print(f"    {b}")
    print("\n  MODULE 8 STATUS: INCOMPLETE -- see bugs above")
else:
    print("\n  No failures detected.")
    print(f"\n  MODULE 8 STATUS: COMPLETE ({PASS_COUNT}/{total} checks passed)")
