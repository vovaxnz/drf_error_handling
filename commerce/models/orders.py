from django.conf import settings

from catalog.models import Product


from django.core.validators import MinValueValidator
from django.db import models


import uuid
from decimal import Decimal

from commerce.statuses import PaymentStatus, QuoteStatus
from commerce.models.quotes import Quote

from django_fsm import FSMField, transition
from django.core.exceptions import ValidationError

from commerce.statuses import OrderStatus
from common.exceptions import DomainError
from django.db.models import F, Sum, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from decimal import Decimal

TERMINAL_STATUSES = {
    OrderStatus.COMPLETED,
}

class Order(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    quote = models.OneToOneField(Quote, on_delete=models.SET_NULL, null=True, blank=True, related_name="order")

    status = FSMField(
        default=OrderStatus.CREATED,
        choices=OrderStatus.choices,
        protected=True,
    )

    currency = models.CharField(max_length=3, default="USD")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))], default=Decimal("0"))

    shipping_address = models.JSONField(default=dict, blank=True)

    placed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["client", "created_at"]),
            models.Index(fields=["status"]),
        ]

    @transition(field=status, source=OrderStatus.CREATED, target=OrderStatus.CONFIRMED, conditions=[lambda x: x.can_be_confirmed])
    def confirm(self): pass

    @transition(field=status, source=OrderStatus.CONFIRMED, target=OrderStatus.IN_PROGRESS)
    def process(self): pass

    @transition(field=status, source=OrderStatus.IN_PROGRESS, target=OrderStatus.SHIPPED)
    def ship(self): pass

    @transition(field=status, source=OrderStatus.SHIPPED, target=OrderStatus.COMPLETED)
    def complete(self): pass

    @transition(field=status, source="*", target=OrderStatus.CANCELLED)
    def cancel(self): pass


    def can_be_confirmed(self):
        if not self.is_fully_paid:
            raise DomainError(
                message="Order {0} cannot be confirmed because it is not fully paid. Required: {1} {2}.".format(
                    self.id, self.total_amount, self.currency
                ),
                code="order_not_fully_paid",
                http_status=400,
            )


    def update_total_price(self):

        self.total_amount = self.items.aggregate(
            total=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F("quantity") * F("unit_price"),
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ),
                Decimal("0"),
            )
        )["total"]

        self.save(update_fields=["total_amount"])

    @property
    def is_fully_paid(self) -> bool:
        required = self.items.aggregate(
            total=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F("quantity") * F("unit_price"),
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ),
                Decimal("0"),
            )
        )["total"]

        received = self.payments.filter(
            status=PaymentStatus.COMPLETED
        ).aggregate(
            total=Coalesce(Sum("amount"), Decimal("0"))
        )["total"]

        return received >= required


    def save(self, *args, **kwargs):

        if self.quote and self.quote.client_id != self.client_id:
            raise DomainError(
                message="Order client {0} does not match quote client {1} for quote {2}.".format(
                    self.client_id, self.quote.client_id, self.quote_id
                ),
                code="client_mismatch",
                http_status=400,
            )
        
        if self._state.adding:

            if self.quote.status != QuoteStatus.ACCEPTED:
                raise DomainError(
                    message="Cannot create order from quote {0} with status {1}. Expected accepted.".format(
                        self.quote.id, self.quote.status
                    ),
                    code="invalid_quote_status",
                    http_status=400,
                )

            if not self.quote.items.exists():
                raise DomainError(
                    message="Cannot create order from empty quote {0}. No items found.".format(
                        self.quote.id
                    ),
                    code="empty_quote",
                    http_status=400,
                )


        else:

            old = Order.objects.only("status").get(pk=self.pk)

            if old.status in TERMINAL_STATUSES:
                raise DomainError(
                    message="Order {0} is in terminal status {1} and cannot be modified.".format(
                        self.pk, old.status
                    ),
                    code="order_terminal_state",
                    http_status=409,
                )

        super().save(*args, **kwargs)


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

    def save(self, *args, **kwargs):
        if self.order.status != OrderStatus.CREATED:
            raise DomainError(
                message="Cannot add item to order {0} because status is {1}. Expected status: created.".format(
                    self.order.id, self.order.status
                ),
                code="order_not_modifiable",
                http_status=400,
            )
        super().save(*args, **kwargs)
        self.order.update_total_price()

    def delete(self, *args, **kwargs):
        if self.order.status in TERMINAL_STATUSES:
            raise DomainError(
                message="Cannot delete item from order {0} because status is {1}.".format(
                    self.order.id, self.order.status
                ),
                code="order_terminal_state",
                http_status=409,
            )
        order = self.order
        super().delete(*args, **kwargs)
        order.update_total_price()

    def __str__(self) -> str:
        title = self.product_title or getattr(self.product, "title", "Product")
        return f"OrderItem {self.id} - {title} x{self.quantity} - {self.unit_price} {self.currency}"