from django.core.validators import MinValueValidator
import uuid
from decimal import Decimal

from django.db import models
from django_fsm import FSMField, transition

from commerce.statuses import OrderStatus
from commerce.statuses import PaymentStatus
from common.exceptions import DomainError


TERMINAL_STATES = [
    PaymentStatus.FAILED,
    PaymentStatus.REFUNDED,
]


class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    order = models.ForeignKey("Order", on_delete=models.CASCADE, related_name="payments")

    status = FSMField(
        default=PaymentStatus.CREATED,
        choices=PaymentStatus.choices,
        protected=True,
    )

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

    @transition(field=status, source=PaymentStatus.CREATED, target=PaymentStatus.PENDING)
    def start_processing(self): pass

    @transition(field=status, source=PaymentStatus.PENDING, target=PaymentStatus.COMPLETED)
    def complete(self): pass

    @transition(field=status, source=PaymentStatus.PENDING, target=PaymentStatus.FAILED)
    def mark_failed(self): pass

    @transition(field=status, source=PaymentStatus.COMPLETED, target=PaymentStatus.REFUND_PENDING)
    def request_refund(self): pass

    @transition(field=status, source=PaymentStatus.REFUND_PENDING, target=PaymentStatus.REFUNDED)
    def refund(self): pass

    @transition(field=status, source="*", target=PaymentStatus.FAILED)
    def fail(self): pass

    def save(self, *args, **kwargs):

        if self._state.adding:
            if self.order.status == OrderStatus.CANCELLED:
                raise DomainError(
                    message="Cannot create payment for cancelled order {0}.".format(
                        self.order.id
                    ),
                    code="order_cancelled",
                    http_status=400,
                )
        
        else:
            old = Payment.objects.only("status").get(pk=self.pk)
            if old.status in TERMINAL_STATES:
               raise DomainError(
                    message="Payment {0} is in terminal status {1} and cannot be modified.".format(
                        self.pk, old.status
                    ),
                    code="payment_terminal_state",
                    http_status=409,
                )

        if self.order.currency != self.currency:
            raise DomainError(
                message="Currency mismatch for payment {0}. Payment currency {1}, order currency {2}, order id {3}.".format(
                    self.id, self.currency, self.order.currency, self.order.id
                ),
                code="currency_mismatch",
                http_status=400,
            )
        
        super().save(*args, **kwargs)


    def __str__(self) -> str:
        return f"Payment {self.id} - {self.provider} - {self.status} - {self.amount} {self.currency}"