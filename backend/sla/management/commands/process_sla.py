"""
Management command: process_sla

Scans GrievanceSLA records and performs three sequential actions:

  PHASE A -- Active SLAs
    - Send reminder notifications at 50%, 75%, 90% of elapsed SLA window.
    - Detect breach: mark ACTIVE -> BREACHED when now >= due_at.
    - Send breach notification to the assigned officer (escalation_level 0 -> 1).

  PHASE B -- Breached SLAs
    - L2 escalation: notify SENIOR_OFFICER when breach duration >= SLA_ESCALATION_L2_HOURS.
    - L3 escalation: notify ADMIN when breach duration >= SLA_ESCALATION_L3_HOURS.

Usage:
    python manage.py process_sla            # live run
    python manage.py process_sla --dry-run  # preview only, no DB writes

Design:
    - Idempotent: deduplication flags and escalation_level prevent duplicate sends.
    - Non-fatal per-record: one SLA's failure is caught, logged, and counted.
    - breached_at is set to sla.due_at (actual breach time), NOT timezone.now(),
      so catch-up runs correctly compute hours-since-breach even when the command
      is first run long after the actual breach.
"""

import logging

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process SLA events: send reminders, detect breaches, escalate."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print planned actions without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now()

        if dry_run:
            self.stdout.write(self.style.WARNING("  [DRY RUN] No database writes will occur."))

        self.stdout.write(
            f"process_sla started at {now.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

        stats = {
            "reminders_sent":    0,
            "breaches_detected": 0,
            "escalations_sent":  0,
            "errors":            0,
        }

        self._phase_a_active(now, dry_run, stats)
        self._phase_b_breached(now, dry_run, stats)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n  Summary: "
                f"reminders={stats['reminders_sent']}  "
                f"breaches={stats['breaches_detected']}  "
                f"escalations={stats['escalations_sent']}  "
                f"errors={stats['errors']}"
            )
        )

    # ------------------------------------------------------------------
    # Phase A: ACTIVE SLAs
    # ------------------------------------------------------------------

    def _phase_a_active(self, now, dry_run, stats):
        from sla.models import GrievanceSLA
        from sla.services.notification_service import send_sla_breach, send_sla_reminder

        active_slas = (
            GrievanceSLA.objects
            .filter(status=GrievanceSLA.Status.ACTIVE)
            .select_related(
                "grievance",
                "grievance__assigned_officer",
                "grievance__department",
            )
        )

        count = active_slas.count()
        self.stdout.write(f"\n[Phase A] Active SLAs to scan: {count}")

        for sla in active_slas:
            try:
                self._process_active_sla(sla, now, dry_run, stats, send_sla_reminder, send_sla_breach)
            except Exception:
                stats["errors"] += 1
                logger.exception("Unexpected error processing active SLA#%s", sla.id)

    def _process_active_sla(self, sla, now, dry_run, stats, send_sla_reminder, send_sla_breach):
        from sla.models import GrievanceSLA  # local import — method has its own scope
        total_secs = (sla.due_at - sla.started_at).total_seconds()
        if total_secs <= 0:
            return

        elapsed_pct = (now - sla.started_at).total_seconds() / total_secs * 100

        # Reminders — sent in order; multiple can fire in the same run if the
        # command was not run for an extended period (catch-up behaviour).
        for pct, flag in [
            (50, "reminder_50_sent"),
            (75, "reminder_75_sent"),
            (90, "reminder_90_sent"),
        ]:
            if elapsed_pct >= pct and not getattr(sla, flag):
                self._print_action(f"REMINDER {pct}%", sla)
                if not dry_run:
                    send_sla_reminder(sla, pct)
                    setattr(sla, flag, True)
                    sla.save(update_fields=[flag, "updated_at"])
                stats["reminders_sent"] += 1

        # Breach detection — use sla.due_at as the authoritative breach timestamp
        # so hours-since-breach is accurate even when the command first runs long
        # after the actual deadline was exceeded.
        if now >= sla.due_at:
            self._print_action("BREACHED", sla)
            if not dry_run:
                sla.status = GrievanceSLA.Status.BREACHED
                sla.breached_at = sla.due_at
                sla.escalation_level = 1
                sla.l1_escalated_at = now
                sla.save(update_fields=[
                    "status", "breached_at",
                    "escalation_level", "l1_escalated_at",
                    "updated_at",
                ])
                send_sla_breach(sla)
            stats["breaches_detected"] += 1

    # ------------------------------------------------------------------
    # Phase B: BREACHED SLAs -- escalation
    # ------------------------------------------------------------------

    def _phase_b_breached(self, now, dry_run, stats):
        from sla.models import GrievanceSLA
        from sla.services.notification_service import send_sla_escalation

        l2_hours = getattr(settings, "SLA_ESCALATION_L2_HOURS", 4)
        l3_hours = getattr(settings, "SLA_ESCALATION_L3_HOURS", 8)

        # Fetch SLAs that still need escalation (level 1 or 2 — not yet fully escalated).
        pending = (
            GrievanceSLA.objects
            .filter(
                status=GrievanceSLA.Status.BREACHED,
                escalation_level__lt=3,
            )
            .select_related(
                "grievance",
                "grievance__assigned_officer",
                "grievance__department",
            )
        )

        count = pending.count()
        self.stdout.write(
            f"\n[Phase B] Breached SLAs pending escalation: {count}"
            f"  (L2 after {l2_hours}h, L3 after {l3_hours}h)"
        )

        for sla in pending:
            try:
                self._process_breached_sla(sla, now, dry_run, stats, send_sla_escalation, l2_hours, l3_hours)
            except Exception:
                stats["errors"] += 1
                logger.exception("Unexpected error processing breached SLA#%s", sla.id)

    def _process_breached_sla(self, sla, now, dry_run, stats, send_sla_escalation, l2_hours, l3_hours):
        if sla.breached_at is None:
            return

        hours_since_breach = (now - sla.breached_at).total_seconds() / 3600

        # L2: notify Senior Officer.
        # Check uses sla.escalation_level which is updated in-memory after L2 fires,
        # so L3 can also fire in the same pass if enough time has elapsed.
        if sla.escalation_level == 1 and hours_since_breach >= l2_hours:
            self._print_action("ESCALATE L2", sla, f"{hours_since_breach:.1f}h since breach")
            if not dry_run:
                ok = send_sla_escalation(sla, level=2)
                if ok:
                    sla.escalation_level = 2
                    sla.l2_escalated_at = now
                    sla.save(update_fields=["escalation_level", "l2_escalated_at", "updated_at"])
            stats["escalations_sent"] += 1

        # L3: notify Department Admin.
        # Uses in-memory escalation_level — catches the case where L2 just fired above.
        if sla.escalation_level == 2 and hours_since_breach >= l3_hours:
            self._print_action("ESCALATE L3", sla, f"{hours_since_breach:.1f}h since breach")
            if not dry_run:
                ok = send_sla_escalation(sla, level=3)
                if ok:
                    sla.escalation_level = 3
                    sla.l3_escalated_at = now
                    sla.save(update_fields=["escalation_level", "l3_escalated_at", "updated_at"])
            stats["escalations_sent"] += 1

    # ------------------------------------------------------------------

    def _print_action(self, action, sla, extra=""):
        grievance = sla.grievance
        line = (
            f"  [{action:<14}]  SLA#{sla.id:<5}  G#{grievance.id:<5}"
            f"  {grievance.priority:<8}  {sla.sla_hours}h"
        )
        if extra:
            line += f"  ({extra})"
        self.stdout.write(line)
