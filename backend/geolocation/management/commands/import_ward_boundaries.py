"""
Management command: import_ward_boundaries

Reads an official Trivandrum Corporation ward boundary GeoJSON or Shapefile
and populates the Ward.boundary field for each matched ward record.

Matching strategy:
  GeoJSON feature property WARD_NO (integer) -> TVM-NNN (zero-padded 3 digits)
  -> matched against Ward.code in the database

Usage:
    python manage.py import_ward_boundaries --file wards.geojson
    python manage.py import_ward_boundaries --file wards.shp --ward-no-field WARD_NUMBER
    python manage.py import_ward_boundaries --file wards.geojson --dry-run

Prerequisites:
    - PostGIS extension enabled on the database
    - Ward records already seeded (run seed_routing_data first)
    - GDAL system library installed and GDAL_LIBRARY_PATH configured in settings
"""

import logging

from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from routing.models import Ward

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import ward boundary geometry from a GeoJSON or Shapefile into Ward.boundary."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            required=True,
            help="Path to the GeoJSON or Shapefile containing ward boundaries.",
        )
        parser.add_argument(
            "--ward-no-field",
            default="WARD_NO",
            help="Name of the feature property that holds the ward number integer. Default: WARD_NO",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report without writing to the database.",
        )

    def handle(self, *args, **options):
        file_path    = options["file"]
        ward_no_field = options["ward_no_field"]
        dry_run      = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN -- no database writes"))

        try:
            ds = DataSource(file_path)
        except Exception as exc:
            raise CommandError(f"Could not open file: {file_path}\n{exc}") from exc

        layer = ds[0]
        self.stdout.write(f"File: {file_path}")
        self.stdout.write(f"Layer: {layer.name} | Features: {len(layer)}")
        self.stdout.write(f"Matching field: {ward_no_field}")
        self.stdout.write("")

        matched   = 0
        unmatched = 0
        errors    = 0

        with transaction.atomic():
            for feature in layer:
                # --- Read ward number from feature ---
                try:
                    ward_no = int(feature[ward_no_field].value)
                except KeyError:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  SKIP: Feature has no field '{ward_no_field}'. "
                            f"Available fields: {layer.fields}"
                        )
                    )
                    errors += 1
                    continue
                except (TypeError, ValueError) as exc:
                    self.stdout.write(
                        self.style.WARNING(f"  SKIP: Cannot parse ward number — {exc}")
                    )
                    errors += 1
                    continue

                code = f"TVM-{ward_no:03d}"

                # --- Match to Ward record ---
                try:
                    ward = Ward.objects.get(code=code)
                except Ward.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f"  NO MATCH: {code} not found in Ward table")
                    )
                    unmatched += 1
                    continue

                # --- Convert geometry to WGS84 GEOS ---
                try:
                    gdal_geom = feature.geom
                    gdal_geom.transform(4326)
                    geos_geom = GEOSGeometry(gdal_geom.wkt, srid=4326)

                    # Ward.boundary is MultiPolygonField; wrap Polygon if needed
                    if isinstance(geos_geom, Polygon):
                        geos_geom = MultiPolygon(geos_geom, srid=4326)
                    elif not isinstance(geos_geom, MultiPolygon):
                        self.stdout.write(
                            self.style.WARNING(
                                f"  SKIP {code}: Unsupported geometry type {geos_geom.geom_type}"
                            )
                        )
                        errors += 1
                        continue

                except Exception as exc:
                    self.stdout.write(
                        self.style.ERROR(f"  ERROR {code}: Geometry conversion failed — {exc}")
                    )
                    errors += 1
                    continue

                # --- Write to database ---
                if dry_run:
                    self.stdout.write(f"  WOULD UPDATE: {code} ({ward.name})")
                else:
                    ward.boundary = geos_geom
                    ward.save(update_fields=["boundary"])
                    self.stdout.write(f"  OK: {code} ({ward.name})")

                matched += 1

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write("")
        self.stdout.write("=== IMPORT SUMMARY ===")
        self.stdout.write(f"  Matched and {'would update' if dry_run else 'updated'}: {matched}")
        self.stdout.write(f"  No matching Ward record:                               {unmatched}")
        self.stdout.write(f"  Skipped (field/geometry errors):                       {errors}")
        self.stdout.write(f"  Total features in file:                                {len(layer)}")

        wards_with_boundary = Ward.objects.exclude(boundary=None).count()
        if not dry_run:
            self.stdout.write("")
            self.stdout.write(
                f"  Wards with boundaries in DB: {wards_with_boundary} / {Ward.objects.count()}"
            )
