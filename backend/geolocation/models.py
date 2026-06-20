from django.db import models
from django.conf import settings


class GeolocationLog(models.Model):
    """
    Audit record written once per grievance at creation time.

    Records the raw GPS coordinates submitted by the citizen, which ward
    was detected (if any), and whether the ward was auto-detected via GPS
    or supplied manually. Raw coordinates are never stored on the Grievance
    model — this is the only table that holds them.

    Retention: raw lat/lng should be anonymised after the audit window
    defined by the data retention policy.
    """

    class DetectionMethod(models.TextChoices):
        GPS_AUTO        = "GPS_AUTO",        "GPS Auto-Detected"
        MANUAL_FALLBACK = "MANUAL_FALLBACK", "Manual Ward Selection"

    grievance = models.OneToOneField(
        "grievances.Grievance",
        on_delete=models.CASCADE,
        related_name="geolocation_log",
    )
    submitted_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text="Raw latitude submitted by the citizen's device.",
    )
    submitted_lng = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        help_text="Raw longitude submitted by the citizen's device.",
    )
    detected_ward = models.ForeignKey(
        "routing.Ward",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="geolocation_logs",
        help_text="Ward found by point-in-polygon lookup. Null if coordinates were outside all boundaries.",
    )
    detection_method = models.CharField(
        max_length=20,
        choices=DetectionMethod.choices,
    )
    accuracy_meters = models.FloatField(
        null=True,
        blank=True,
        help_text="Device-reported GPS accuracy radius in metres, if provided.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Geolocation Log"
        verbose_name_plural = "Geolocation Logs"

    def __str__(self):
        return f"Grievance #{self.grievance_id} — {self.detection_method}"
