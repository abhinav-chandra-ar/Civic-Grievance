from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from .managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):

    class Role(models.TextChoices):
        CITIZEN = "CITIZEN", "Citizen"
        JUNIOR_OFFICER = "JUNIOR_OFFICER", "Junior Officer"
        SENIOR_OFFICER = "SENIOR_OFFICER", "Senior Officer"
        ADMIN = "ADMIN", "Admin"

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CITIZEN
    )

    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="officers",
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email