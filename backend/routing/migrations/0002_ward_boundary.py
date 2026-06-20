import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):
    """
    Adds a nullable MultiPolygonField (WGS84) to the Ward model.

    Infrastructure prerequisite: PostGIS extension must already be enabled
    on the database before this migration runs.
    Verify: SELECT extname FROM pg_extension WHERE extname = 'postgis';

    Boundary data is populated separately via:
        python manage.py import_ward_boundaries --file wards.geojson
    """

    dependencies = [
        ('routing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='ward',
            name='boundary',
            field=django.contrib.gis.db.models.fields.MultiPolygonField(
                blank=True,
                null=True,
                srid=4326,
                help_text='WGS84 ward boundary polygon. Populated by import_ward_boundaries command.',
            ),
        ),
    ]
