"""
Management command: seed_routing_data

Populates the routing tables for Trivandrum Corporation MVP:
  - 5 Departments  (adds KSEB if missing; leaves existing 4 untouched)
  - 5 Jurisdictions (Central, North, South, East, West)
  - 100 Wards      (56 VERIFIED + 44 PLACEHOLDER)
  - 500 RoutingRules (100 wards x 5 ML categories)

Fully idempotent: safe to run multiple times with no side effects.

Usage:
    python manage.py seed_routing_data
    python manage.py seed_routing_data --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from departments.models import Department
from routing.models import Jurisdiction, RoutingRule, Ward


# ---------------------------------------------------------------------------
# Departments required by the ML pipeline
# name must match Department.name in the DB (display name, not ML code)
# ---------------------------------------------------------------------------
DEPARTMENTS = [
    "KSEB",
    "KWA",
    "PWD",
    "Public Health",
    "Local Self Government",
]

# ---------------------------------------------------------------------------
# ML category codes -> Department display names
# These are the exact strings emitted by ml_engine/processors/department.py
# ---------------------------------------------------------------------------
CATEGORY_TO_DEPT = {
    "KSEB":          "KSEB",
    "KWA":           "KWA",
    "PWD":           "PWD",
    "PUBLIC_HEALTH": "Public Health",
    "LSG":           "Local Self Government",
}

# ---------------------------------------------------------------------------
# Jurisdiction names
# ---------------------------------------------------------------------------
JURISDICTIONS = ["Central", "North", "South", "East", "West"]

# ---------------------------------------------------------------------------
# Ward seed data
# Format: (code, name, jurisdiction_name)
#
# Status key embedded in name:
#   Names without "PLACEHOLDER" prefix = VERIFIED Corporation wards
#   Names with "PLACEHOLDER-" prefix   = structural placeholders
#                                         (official name not confirmed)
#
# CENTRAL ZONE — TVM-001 to TVM-020  (15 verified + 5 placeholder)
# EAST ZONE    — TVM-021 to TVM-045  (15 verified + 10 placeholder)
# NORTH ZONE   — TVM-046 to TVM-070  (12 verified + 13 placeholder)
# SOUTH ZONE   — TVM-071 to TVM-087  ( 6 verified + 11 placeholder)
# WEST ZONE    — TVM-088 to TVM-100  ( 8 verified +  5 placeholder)
# ---------------------------------------------------------------------------
WARDS = [
    # --- CENTRAL ZONE (TVM-001 to TVM-020) ---
    ("TVM-001", "Fort",                     "Central"),
    ("TVM-002", "East Fort",                "Central"),
    ("TVM-003", "Attakulangara",            "Central"),
    ("TVM-004", "Chalai",                   "Central"),
    ("TVM-005", "Killippalam",              "Central"),
    ("TVM-006", "Manacaud",                 "Central"),
    ("TVM-007", "Thampanoor",               "Central"),
    ("TVM-008", "Palayam",                  "Central"),
    ("TVM-009", "Statue",                   "Central"),
    ("TVM-010", "Vanchiyoor",               "Central"),
    ("TVM-011", "Thycaud",                  "Central"),
    ("TVM-012", "Jagathy",                  "Central"),
    ("TVM-013", "Museum",                   "Central"),
    ("TVM-014", "Park",                     "Central"),
    ("TVM-015", "Chakkai",                  "Central"),
    ("TVM-016", "PLACEHOLDER-CENTRAL-01",   "Central"),
    ("TVM-017", "PLACEHOLDER-CENTRAL-02",   "Central"),
    ("TVM-018", "PLACEHOLDER-CENTRAL-03",   "Central"),
    ("TVM-019", "PLACEHOLDER-CENTRAL-04",   "Central"),
    ("TVM-020", "PLACEHOLDER-CENTRAL-05",   "Central"),

    # --- EAST ZONE (TVM-021 to TVM-045) ---
    ("TVM-021", "Vazhuthacaud",             "East"),
    ("TVM-022", "Vellayambalam",            "East"),
    ("TVM-023", "Kowdiar",                  "East"),
    ("TVM-024", "Nanthancode",              "East"),
    ("TVM-025", "Pattom",                   "East"),
    ("TVM-026", "Kesavadasapuram",          "East"),
    ("TVM-027", "Medical College",          "East"),
    ("TVM-028", "Ambalamukku",              "East"),
    ("TVM-029", "Kumarapuram",              "East"),
    ("TVM-030", "Kudappanakunnu",           "East"),
    ("TVM-031", "Peroorkada",               "East"),
    ("TVM-032", "Karamana",                 "East"),
    ("TVM-033", "Kannammoola",              "East"),
    ("TVM-034", "Pappanamcode",             "East"),
    ("TVM-035", "Mannanthala",              "East"),
    ("TVM-036", "PLACEHOLDER-EAST-01",      "East"),
    ("TVM-037", "PLACEHOLDER-EAST-02",      "East"),
    ("TVM-038", "PLACEHOLDER-EAST-03",      "East"),
    ("TVM-039", "PLACEHOLDER-EAST-04",      "East"),
    ("TVM-040", "PLACEHOLDER-EAST-05",      "East"),
    ("TVM-041", "PLACEHOLDER-EAST-06",      "East"),
    ("TVM-042", "PLACEHOLDER-EAST-07",      "East"),
    ("TVM-043", "PLACEHOLDER-EAST-08",      "East"),
    ("TVM-044", "PLACEHOLDER-EAST-09",      "East"),
    ("TVM-045", "PLACEHOLDER-EAST-10",      "East"),

    # --- NORTH ZONE (TVM-046 to TVM-070) ---
    ("TVM-046", "Enchakkal",                "North"),
    ("TVM-047", "Thirumala",                "North"),
    ("TVM-048", "Mudavanmughal",            "North"),
    ("TVM-049", "Vattiyoorkavu",            "North"),
    ("TVM-050", "Ulloor",                   "North"),
    ("TVM-051", "Sreekaryam",               "North"),
    ("TVM-052", "Kazhakoottam",             "North"),
    ("TVM-053", "Karyavattom",              "North"),
    ("TVM-054", "Pravachambalam",           "North"),
    ("TVM-055", "Peyad",                    "North"),
    ("TVM-056", "Thonnakkal",               "North"),
    ("TVM-057", "Naruvamoodu",              "North"),
    ("TVM-058", "PLACEHOLDER-NORTH-01",     "North"),
    ("TVM-059", "PLACEHOLDER-NORTH-02",     "North"),
    ("TVM-060", "PLACEHOLDER-NORTH-03",     "North"),
    ("TVM-061", "PLACEHOLDER-NORTH-04",     "North"),
    ("TVM-062", "PLACEHOLDER-NORTH-05",     "North"),
    ("TVM-063", "PLACEHOLDER-NORTH-06",     "North"),
    ("TVM-064", "PLACEHOLDER-NORTH-07",     "North"),
    ("TVM-065", "PLACEHOLDER-NORTH-08",     "North"),
    ("TVM-066", "PLACEHOLDER-NORTH-09",     "North"),
    ("TVM-067", "PLACEHOLDER-NORTH-10",     "North"),
    ("TVM-068", "PLACEHOLDER-NORTH-11",     "North"),
    ("TVM-069", "PLACEHOLDER-NORTH-12",     "North"),
    ("TVM-070", "PLACEHOLDER-NORTH-13",     "North"),

    # --- SOUTH ZONE (TVM-071 to TVM-087) ---
    ("TVM-071", "Nemom",                    "South"),
    ("TVM-072", "Kalliyoor",                "South"),
    ("TVM-073", "Thumba",                   "South"),
    ("TVM-074", "Beemapally",               "South"),
    ("TVM-075", "Vizhinjam",                "South"),
    ("TVM-076", "Kovalam",                  "South"),
    ("TVM-077", "PLACEHOLDER-SOUTH-01",     "South"),
    ("TVM-078", "PLACEHOLDER-SOUTH-02",     "South"),
    ("TVM-079", "PLACEHOLDER-SOUTH-03",     "South"),
    ("TVM-080", "PLACEHOLDER-SOUTH-04",     "South"),
    ("TVM-081", "PLACEHOLDER-SOUTH-05",     "South"),
    ("TVM-082", "PLACEHOLDER-SOUTH-06",     "South"),
    ("TVM-083", "PLACEHOLDER-SOUTH-07",     "South"),
    ("TVM-084", "PLACEHOLDER-SOUTH-08",     "South"),
    ("TVM-085", "PLACEHOLDER-SOUTH-09",     "South"),
    ("TVM-086", "PLACEHOLDER-SOUTH-10",     "South"),
    ("TVM-087", "PLACEHOLDER-SOUTH-11",     "South"),

    # --- WEST ZONE (TVM-088 to TVM-100) ---
    ("TVM-088", "Valiyathura",              "West"),
    ("TVM-089", "Poonthura",                "West"),
    ("TVM-090", "Vallakadavu",              "West"),
    ("TVM-091", "Muttathara",               "West"),
    ("TVM-092", "Veli",                     "West"),
    ("TVM-093", "Akkulam",                  "West"),
    ("TVM-094", "Shanghumugham",            "West"),
    ("TVM-095", "Kochuveli",                "West"),
    ("TVM-096", "PLACEHOLDER-WEST-01",      "West"),
    ("TVM-097", "PLACEHOLDER-WEST-02",      "West"),
    ("TVM-098", "PLACEHOLDER-WEST-03",      "West"),
    ("TVM-099", "PLACEHOLDER-WEST-04",      "West"),
    ("TVM-100", "PLACEHOLDER-WEST-05",      "West"),
]


class Command(BaseCommand):
    help = (
        "Seed Trivandrum Corporation routing data: "
        "5 departments, 5 jurisdictions, 100 wards, 500 routing rules. "
        "Fully idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be created without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no database writes"))

        with transaction.atomic():
            dept_map = self._seed_departments(dry_run)
            jur_map  = self._seed_jurisdictions(dry_run)
            ward_map = self._seed_wards(jur_map, dry_run)
            self._seed_routing_rules(ward_map, jur_map, dept_map, dry_run)

            if dry_run:
                # Roll back everything so the DB stays clean
                transaction.set_rollback(True)

        self._print_summary(dry_run)

    # ------------------------------------------------------------------
    # Step 1 — Departments
    # ------------------------------------------------------------------
    def _seed_departments(self, dry_run):
        self.stdout.write("\n[1/4] Departments")
        dept_map = {}
        created_count = 0

        for name in DEPARTMENTS:
            if dry_run:
                exists = Department.objects.filter(name=name).exists()
                action = "exists" if exists else "WOULD CREATE"
                self.stdout.write(f"  {name}: {action}")
                dept_map[name] = None
            else:
                obj, created = Department.objects.get_or_create(
                    name=name,
                    defaults={"description": ""},
                )
                dept_map[name] = obj
                if created:
                    created_count += 1
                    self.stdout.write(f"  {self.style.SUCCESS('CREATED')} {name}")
                else:
                    self.stdout.write(f"  {name}: already exists (id={obj.id})")

        if not dry_run:
            self.stdout.write(f"  -> {created_count} created, {len(DEPARTMENTS) - created_count} already existed")
        return dept_map

    # ------------------------------------------------------------------
    # Step 2 — Jurisdictions
    # ------------------------------------------------------------------
    def _seed_jurisdictions(self, dry_run):
        self.stdout.write("\n[2/4] Jurisdictions")
        jur_map = {}
        created_count = 0

        for name in JURISDICTIONS:
            if dry_run:
                exists = Jurisdiction.objects.filter(name=name).exists()
                action = "exists" if exists else "WOULD CREATE"
                self.stdout.write(f"  {name}: {action}")
                jur_map[name] = None
            else:
                obj, created = Jurisdiction.objects.get_or_create(name=name)
                jur_map[name] = obj
                if created:
                    created_count += 1
                    self.stdout.write(f"  {self.style.SUCCESS('CREATED')} {name}")
                else:
                    self.stdout.write(f"  {name}: already exists (id={obj.id})")

        if not dry_run:
            self.stdout.write(f"  -> {created_count} created, {len(JURISDICTIONS) - created_count} already existed")
        return jur_map

    # ------------------------------------------------------------------
    # Step 3 — Wards
    # ------------------------------------------------------------------
    def _seed_wards(self, jur_map, dry_run):
        self.stdout.write("\n[3/4] Wards")
        ward_map = {}
        created_count = 0
        skipped_count = 0

        for code, name, zone in WARDS:
            jurisdiction = jur_map.get(zone)

            if dry_run:
                exists = Ward.objects.filter(code=code).exists()
                action = "exists" if exists else "WOULD CREATE"
                tag = "" if "PLACEHOLDER" not in name else " [PLACEHOLDER]"
                self.stdout.write(f"  {code} {name}{tag}: {action}")
                ward_map[code] = None
                continue

            obj, created = Ward.objects.get_or_create(
                code=code,
                defaults={"name": name},
            )
            ward_map[code] = obj

            if created:
                created_count += 1
            else:
                skipped_count += 1

        if not dry_run:
            placeholder_count = sum(1 for _, n, _ in WARDS if "PLACEHOLDER" in n)
            verified_count = len(WARDS) - placeholder_count
            self.stdout.write(
                f"  -> {created_count} created ({verified_count} verified + "
                f"{placeholder_count} placeholder), {skipped_count} already existed"
            )
        return ward_map

    # ------------------------------------------------------------------
    # Step 4 — RoutingRules (100 wards × 5 categories = 500 rules)
    # ------------------------------------------------------------------
    def _seed_routing_rules(self, ward_map, jur_map, dept_map, dry_run):
        self.stdout.write("\n[4/4] RoutingRules")
        created_count = 0
        skipped_count = 0

        for code, _name, zone in WARDS:
            ward = ward_map.get(code)
            jurisdiction = jur_map.get(zone)

            for category, dept_name in CATEGORY_TO_DEPT.items():
                department = dept_map.get(dept_name)

                if dry_run:
                    # Just count — don't print 500 lines
                    created_count += 1
                    continue

                _rule, created = RoutingRule.objects.get_or_create(
                    ward=ward,
                    category=category,
                    defaults={
                        "department": department,
                        "jurisdiction": jurisdiction,
                    },
                )
                if created:
                    created_count += 1
                else:
                    skipped_count += 1

        if dry_run:
            self.stdout.write(f"  WOULD CREATE up to {created_count} routing rules")
        else:
            self.stdout.write(
                f"  -> {created_count} created, {skipped_count} already existed"
            )

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    def _print_summary(self, dry_run):
        self.stdout.write("")
        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY RUN COMPLETE — nothing written ==="))
            return

        from departments.models import Department as D
        from routing.models import Jurisdiction as J, Ward as W, RoutingRule as RR

        dept_count = D.objects.count()
        jur_count  = J.objects.count()
        ward_count = W.objects.count()
        rule_count = RR.objects.count()
        placeholder_count = W.objects.filter(name__startswith="PLACEHOLDER").count()
        verified_count = ward_count - placeholder_count

        self.stdout.write(self.style.SUCCESS("=== SEED COMPLETE ==="))
        self.stdout.write(f"  Departments   : {dept_count} (expected 5)")
        self.stdout.write(f"  Jurisdictions : {jur_count} (expected 5)")
        self.stdout.write(f"  Wards         : {ward_count} (expected 100)")
        self.stdout.write(f"    Verified    : {verified_count}")
        self.stdout.write(f"    Placeholder : {placeholder_count}")
        self.stdout.write(f"  RoutingRules  : {rule_count} (expected 500)")

        ok = dept_count == 5 and jur_count == 5 and ward_count == 100 and rule_count == 500
        if ok:
            self.stdout.write(self.style.SUCCESS("\n  ALL COUNTS CORRECT. Routing is ready for MVP testing."))
        else:
            self.stdout.write(self.style.ERROR("\n  COUNT MISMATCH — review output above."))
