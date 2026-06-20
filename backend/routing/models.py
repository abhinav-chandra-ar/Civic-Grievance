from django.db import models

from departments.models import Department


class Ward(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.code} - {self.name}"


class Jurisdiction(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class RoutingRule(models.Model):
    ward = models.ForeignKey(
        Ward,
        on_delete=models.CASCADE,
        related_name="routing_rules",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="routing_rules",
    )
    jurisdiction = models.ForeignKey(
        Jurisdiction,
        on_delete=models.CASCADE,
        related_name="routing_rules",
    )
    category = models.CharField(
        max_length=50,
        help_text="Matches ml_department_suggestion values: KSEB, KWA, PWD, PUBLIC_HEALTH, LSG",
    )

    class Meta:
        unique_together = ("ward", "category")

    def __str__(self):
        return f"{self.ward} / {self.category} -> {self.department} ({self.jurisdiction})"
