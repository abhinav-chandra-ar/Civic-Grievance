"""
Management command: seed_sla_policies

Creates system-default SLAPolicy records (department=None) for each
priority level if they do not already exist.

Run once after first deployment:
    python manage.py seed_sla_policies

Safe to re-run — uses get_or_create, so existing records are untouched.
"""

from django.core.management.base import BaseCommand

from sla.models import SLAPolicy

_DEFAULTS = [
    ("CRITICAL", 24),
    ("HIGH",     48),
    ("MEDIUM",   72),
    ("LOW",      120),
]


class Command(BaseCommand):
    help = "Seed system-default SLA policies for all four priority levels."

    def handle(self, *args, **options):
        created_count = 0
        skipped_count = 0

        for priority, hours in _DEFAULTS:
            policy, created = SLAPolicy.objects.get_or_create(
                department=None,
                priority=priority,
                is_active=True,
                defaults={"sla_hours": hours},
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Created : DEFAULT | {priority:<8} | {hours}h"
                    )
                )
                created_count += 1
            else:
                self.stdout.write(
                    f"  Skipped : DEFAULT | {priority:<8} | {policy.sla_hours}h  (already exists)"
                )
                skipped_count += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {created_count} created, {skipped_count} already existed."
            )
        )
