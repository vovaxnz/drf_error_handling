from django_fsm import FSMField, transition

from catalog.models import Product
from django.db import transaction


from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


import uuid
from decimal import Decimal

from commerce.statuses import QuoteStatus
from common.exceptions import DomainError
from django.db.models import F, Sum, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from decimal import Decimal

class QuoteItem(models.Model):
    """
    Snapshot prices at the time of Quote formation.
    Next, Quote -> Order, and OrderItem duplicates the snapshot at the time of purchase.

    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    quote = models.ForeignKey("Quote", on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.PROTECT, related_name="quote_items")

    quantity = models.PositiveIntegerField(default=1)

    unit_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])
    currency = models.CharField(max_length=3, default="USD", editable=False)

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


    def delete(self, *args, **kwargs):
        quote = self.quote
        super().delete(*args, **kwargs)
        quote.total_amount = quote.get_total_price()
        quote.save(update_fields=["total_amount", "updated_at"])


class Quote(models.Model):
    """
    The only source of truth for money for UI/checkout.
    Allows you to show the user the exact amount and then converts it to an Order.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quotes")

    status = FSMField(
        default=QuoteStatus.DRAFT,
        choices=QuoteStatus.choices,
        protected=True,
    )
    
    currency = models.CharField(max_length=3, default="USD", editable=False)
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

    @transition(field=status, source=QuoteStatus.DRAFT, target=QuoteStatus.SENT, conditions=[lambda x: x.can_be_sent])
    def send(self): pass

    @transition(field=status, source=QuoteStatus.SENT, target=QuoteStatus.ACCEPTED)
    def accept(self): pass

    @transition(field=status, source=QuoteStatus.SENT, target=QuoteStatus.REJECTED)
    def reject(self): pass


    def __str__(self) -> str:
        client = getattr(self.client, "email", "") or getattr(self.client, "username", "")
        return f"Quote {self.id} - {client} - {self.status} - {self.total_amount} {self.currency}"

    def add_item(self, product: Product, quantity: int):
        if quantity <= 0:
            raise DomainError(
                message="Invalid quantity {0} for product {1}. Quantity must be positive.".format(
                    quantity, product.id
                ),
                code="invalid_quantity",
                http_status=400,
            )

        if not product.is_active:
            raise DomainError(
                message="Product {0} with SKU {1} is inactive and cannot be added to quote {2}.".format(
                    product.id, product.sku, self.id
                ),
                code="product_inactive",
                http_status=400,
            )


        if self.status != QuoteStatus.DRAFT:
            raise DomainError(
                message="Cannot add items to quote {0} because its status is {1}, expected draft.".format(
                    self.id, self.status
                ),
                code="quote_not_draft",
                http_status=400,
            )


        if product.price_currency != self.currency:
            raise DomainError(
                message="Currency mismatch for quote {0}. Product currency {1}, quote currency {2}.".format(
                    self.id, product.price_currency, self.currency
                ),
                code="currency_mismatch",
                http_status=400,
            )
        
        with transaction.atomic():
            quote_item, created = QuoteItem.objects.select_for_update().get_or_create(
                quote=self,
                product=product,
                defaults={
                    "quantity": quantity,
                    "unit_price": product.price_amount,
                    "currency": self.currency,
                },
            )

            if not created:
                quote_item.quantity += quantity
                quote_item.save(update_fields=["quantity"])

            self.total_amount = self.get_total_price()
            self.save(update_fields=["total_amount", "updated_at"])


    def save(self, *args, **kwargs):
        if not self._state.adding:

            old = Quote.objects.only("status").get(pk=self.pk)

            if old.status == QuoteStatus.ACCEPTED:
                raise DomainError(
                    message="Quote {0} is already accepted and cannot be modified. Current status: {1}.".format(
                        self.pk, old.status
                    ),
                    code="quote_already_accepted",
                    http_status=409,
                )
            
        super().save(*args, **kwargs)


    def get_total_price(self) -> Decimal:
        total = self.items.aggregate(
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

        return total
    

    def can_be_sent(self):
        total_price = self.get_total_price()
        if total_price == 0:
            raise DomainError(
                message=f"Cannot send quote {self.id} because total amount is {total_price}.",
                code="empty_quote",
                http_status=400,
            )
        return True