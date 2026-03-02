# commerce/views.py
from rest_framework import viewsets

from .models.quotes import Quote
from .models.orders import Order, OrderItem
from .models.payments import Payment
from common.serializers import crud_schema
from .models.quotes import QuoteItem
from .serializers import (
    QuoteSerializer,
    OrderSerializer,
    PaymentSerializer,
)
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema_view, extend_schema
from .models.quotes import Quote
from .models.orders import Order
from .models.payments import Payment

@extend_schema_view(
    list=extend_schema(
        description=(
            "Quote aggregate root.\n\n"
            "Invariants:\n"
            "- Items may be added only in draft state\n"
            "- Empty quote cannot be sent\n"
            "- Accepted quote becomes immutable\n"
            "- Quote currency fixed at creation\n\n"
        )
    )
)
@crud_schema(QuoteSerializer)
class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.select_related("client").all().order_by("-created_at")
    serializer_class = QuoteSerializer

    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        quote = self.get_object()
        quote.send()
        quote.save()
        return Response(self.get_serializer(quote).data)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        quote = self.get_object()

        quote.accept()
        quote.save()

        idempotency_key = request.data.get("idempotency_key")
        if not idempotency_key:
            raise DomainError("idempotency_key is required")

        order = OrderService.create_from_quote(
            quote=quote,
            client=quote.client,
            idempotency_key=idempotency_key,
        )

        return Response(
            {
                "quote": self.get_serializer(quote).data,
                "order_id": order.id,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        quote = self.get_object()
        quote.reject()
        quote.save()
        return Response(self.get_serializer(quote).data)



@extend_schema_view(
    list=extend_schema(
        description=(
            "Order aggregate root.\n\n"
            "Invariants:\n"
            "- Must originate from accepted Quote\n"
            "- Idempotency key unique per client\n"
            "- Confirm requires full payment\n"
            "- Completed order cannot be modified\n"
            "- Client must match Quote client\n\n"
        )
    )
)
@crud_schema(OrderSerializer)
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related("client", "quote").all().order_by("-created_at")
    serializer_class = OrderSerializer

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        order = self.get_object()
        order.confirm()
        order.placed_at = timezone.now()
        order.save()
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        order = self.get_object()
        order.process()
        order.save()
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    def mark_shipped(self, request, pk=None):
        order = self.get_object()
        order.ship()
        order.save()
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        order = self.get_object()
        order.complete()
        order.save()
        return Response(self.get_serializer(order).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        order.cancel()
        order.save()
        return Response(self.get_serializer(order).data)



@extend_schema_view(
    list=extend_schema(
        description=(
            "Payment entity.\n\n"
            "Invariants:\n"
            "- Currency must match Order.currency\n"
            "- Unique provider + idempotency_key\n"
            "- Cannot modify payment in terminal state\n"
            "- Cannot create payment for cancelled order\n\n"
        )
    )
)
@crud_schema(PaymentSerializer)
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("order").all().order_by("-created_at")
    serializer_class = PaymentSerializer

    @action(detail=True, methods=["post"])
    def create_payment(self, request, pk=None):
        payment = self.get_object()
        payment.save()
        return Response(self.get_serializer(payment).data)

    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        payment = self.get_object()
        payment.start_processing()
        payment.save()
        return Response(self.get_serializer(payment).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        payment = self.get_object()
        payment.complete()
        payment.paid_at = timezone.now()
        payment.save()
        return Response(self.get_serializer(payment).data)

    @action(detail=True, methods=["post"])
    def request_refund(self, request, pk=None):
        payment = self.get_object()
        payment.request_refund()
        payment.save()
        return Response(self.get_serializer(payment).data)