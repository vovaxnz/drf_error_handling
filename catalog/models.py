
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q



class ProductCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        if self.parent_id:
            return f"{self.parent.name} / {self.name}"
        return self.name




class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="products")

    title = models.CharField(max_length=512)
    description = models.TextField(blank=True, default="")

    sku = models.CharField(max_length=128)
    product_url = models.URLField(blank=True, default="")
    image_url = models.URLField(blank=True, default="")

    price_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    price_currency = models.CharField(max_length=3, default="USD", editable=False)

    attributes = models.JSONField(default=dict, blank=True)  # color/material/dimensions, etc.
    embedding_ref = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Link/key to embedding in a separate repository, or empty for MVP",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["sku"], name="uniq_product_sku"),
        ]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["category"]),
            models.Index(fields=["sku"]),
        ]


    def __str__(self) -> str:
        return f"{self.title} - {self.sku}"