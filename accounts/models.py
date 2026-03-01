
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q


class UserRole(models.TextChoices):
    CLIENT = "client", "Client"
    ADMIN = "admin", "Admin"


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=16, choices=UserRole.choices, default=UserRole.CLIENT)

    class Meta:
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self) -> str:
        if self.email:
            return f"{self.username} ({self.email})"
        return self.username