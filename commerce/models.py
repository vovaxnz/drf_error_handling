
import uuid
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q

from catalog.models import Product



class QuoteStatus(models.TextChoices):
    OPEN = "open", "Open"
    FROZEN = "frozen", "Frozen"
    CONVERTED = "converted", "Converted"
    EXPIRED = "expired", "Expired"


class Quote(models.Model):
    """
    The only source of truth for money for UI/checkout.
    Allows you to show the user the exact amount and then converts it to an Order.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quotes")


    status = models.CharField(max_length=16, choices=QuoteStatus.choices, default=QuoteStatus.OPEN)

    currency = models.CharField(max_length=3, default="USD")
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        default=Decimal("0"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["client", "status"]),
        ]

    def __str__(self) -> str:
        client = getattr(self.client, "email", "") or getattr(self.client, "username", "")
        return f"Quote {self.id} - {client} - {self.status} - {self.total_amount} {self.currency}"


class QuoteItem(models.Model):
    """
    Snapshot prices at the time of Quote formation.
    Next, Quote -> Order, and OrderItem duplicates the snapshot at the time of purchase.

    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="quote_items")

    quantity = models.PositiveIntegerField(default=1)

    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    currency = models.CharField(max_length=3, default="USD")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["quote", "product"], name="uniq_quote_product"),
        ]
        indexes = [
            models.Index(fields=["quote"]),
            models.Index(fields=["product"]),
        ]

    def __str__(self) -> str:
        product_title = getattr(self.product, "title", "Product")
        return f"QuoteItem {self.id} - {product_title} x{self.quantity} - {self.unit_price} {self.currency}"



class OrderStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PLACED = "placed", "Placed"
    ALL_RECEIVED = "all_received", "All received"
    SHIPPED = "shipped", "Shipped"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"


class Order(models.Model):
    """
    Create transactionally and idempotently (idempotency_key is unique within the client).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    quote = models.OneToOneField(Quote, on_delete=models.SET_NULL, null=True, blank=True, related_name="order")

    status = models.CharField(max_length=32, choices=OrderStatus.choices, default=OrderStatus.DRAFT)

    currency = models.CharField(max_length=3, default="USD")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))], default=Decimal("0"))

    shipping_address = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=64)

    placed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["client", "idempotency_key"], name="uniq_order_client_idempotency_key"),
        ]
        indexes = [
            models.Index(fields=["client", "created_at"]),
            models.Index(fields=["status"]),
        ]


    def __str__(self) -> str:
        client = getattr(self.client, "email", "") or getattr(self.client, "username", "")
        return f"Order {self.id} - {client} - {self.status} - {self.total_amount} {self.currency}"


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items")

    quantity = models.PositiveIntegerField(default=1)

    # Snapshot of fields at the time of purchase
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    currency = models.CharField(max_length=3, default="USD")

    product_title = models.CharField(max_length=512)
    sku = models.CharField(max_length=128)
    product_url = models.URLField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["sku"]),
        ]

    def __str__(self) -> str:
        title = self.product_title or getattr(self.product, "title", "Product")
        return f"OrderItem {self.id} - {title} x{self.quantity} - {self.unit_price} {self.currency}"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class Payment(models.Model):
    """
    Idempotency: provider + idempotency_key or order + idempotency_key.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")

    status = models.CharField(max_length=16, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    currency = models.CharField(max_length=3, default="USD")

    provider = models.CharField(max_length=64, default="dummy")
    provider_reference = models.CharField(max_length=128, blank=True, default="")

    paid_at = models.DateTimeField(null=True, blank=True)

    idempotency_key = models.CharField(max_length=64)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["provider", "idempotency_key"], name="uniq_payment_provider_idem"),
        ]
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["status"]),
            models.Index(fields=["provider_reference"]),
        ]

    def __str__(self) -> str:
        return f"Payment {self.id} - {self.provider} - {self.status} - {self.amount} {self.currency}"