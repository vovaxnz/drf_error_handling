# commerce/views.py
from rest_framework import viewsets

from .models.quotes import Quote
from .models.orders import Order, OrderItem
from .models.payments import Payment
from common.serializers import ErrorSerializer, crud_schema
from .models.quotes import QuoteItem
from .serializers import (
    OrderItemSerializer,
    QuoteItemSerializer,
    QuoteSerializer,
    OrderSerializer,
    PaymentSerializer,
)
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiResponse, extend_schema_view, extend_schema
from .models.quotes import Quote
from .models.orders import Order
from .models.payments import Payment

from rest_framework import status
from commerce.services.order_service import OrderService

from idempotency_key.decorators import idempotency_key
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes


@extend_schema_view(
    list=extend_schema(
        description=(
            "Quote aggregate root.\n\n"
            "Represents a client pricing snapshot that can be reviewed and later converted to an Order.\n\n"
            "State machine:\n"
            "draft -> sent -> accepted\n"
            "draft -> sent -> rejected\n\n"
            "Only DRAFT quotes are editable. ACCEPTED quotes are immutable.\n"
        )
    )
)
@crud_schema(QuoteSerializer)
class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.select_related("client").all().order_by("-created_at")
    serializer_class = QuoteSerializer

    @extend_schema(
        description=(
            "Transition draft -> sent.\n\n"
            "Invariants:\n"
            "- Quote must be in DRAFT state.\n"
            "- Quote must contain at least one item.\n"
        ),
        responses={
            200: QuoteSerializer,
            400: ErrorSerializer,
            401: ErrorSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
        },
    )
    @action(detail=True, methods=["post"])
    def send(self, request, pk=None):
        quote = self.get_object()
        quote.send()
        quote.save()
        return Response(self.get_serializer(quote).data)

    @extend_schema(
        description=(
            "Transition sent -> accepted and create Order.\n\n"
            "Invariants:\n"
            "- Quote must be in SENT state.\n"
            "- Quote must contain at least one item.\n"
        ),
        responses={
            201: OpenApiResponse(description="Quote accepted and Order created"),
            400: ErrorSerializer,
            401: ErrorSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
            409: ErrorSerializer,
        },
    )
    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        quote = self.get_object()

        quote.accept()
        quote.save()


        order = OrderService.create_from_quote(
            quote=quote,
            client=quote.client,
        )

        return Response(
            {
                "quote": self.get_serializer(quote).data,
                "order_id": order.id,
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        description=(
            "Transition sent -> rejected.\n\n"
            "Invariants:\n"
            "- Quote must be in SENT state.\n"
        ),
        responses={
            200: QuoteSerializer,
            400: ErrorSerializer,
            401: ErrorSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
        },
    )
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        quote = self.get_object()
        quote.reject()
        quote.save()
        return Response(self.get_serializer(quote).data)

    @action(detail=True, methods=["post"])
    def add_item(self, request, pk=None):
        quote = self.get_object()
        product_id = request.data["product"]
        quantity = int(request.data["quantity"])

        product = Product.objects.get(pk=product_id)
        quote.add_item(product, quantity)

        return Response(self.get_serializer(quote).data)

class QuoteItemViewSet(viewsets.ModelViewSet):
    queryset = QuoteItem.objects.select_related("quote", "product")
    serializer_class = QuoteItemSerializer


@extend_schema_view(
    list=extend_schema(
        description=(
            "Order aggregate root.\n\n"
            "Created from an ACCEPTED Quote and represents a purchase lifecycle.\n\n"
            "State machine:\n"
            "created -> confirmed -> in_progress -> shipped -> completed\n\n"
            "created/confirmed/in_progress/shipped -> cancelled\n\n"
            "Orders enforce payment and lifecycle integrity rules.\n"
        )
    )
)
@crud_schema(OrderSerializer)
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related("client", "quote").all().order_by("-created_at")
    serializer_class = OrderSerializer

    @extend_schema(
        description=(
            "Transition created -> confirmed.\n\n"
            "Invariants:\n"
            "- Order must be in CREATED state.\n"
            "- Order must be fully paid.\n"
        ),
        responses={
            200: OrderSerializer,
            400: ErrorSerializer,
            401: ErrorSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
            409: ErrorSerializer,
        },
    )
    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        order = self.get_object()
        order.confirm()
        order.placed_at = timezone.now()
        order.save()
        return Response(self.get_serializer(order).data)

    @extend_schema(
        description=(
            "Transition confirmed -> in_progress.\n\n"
            "Invariants:\n"
            "- Order must be in CONFIRMED state.\n"
        ),
        responses={
            200: OrderSerializer,
            400: ErrorSerializer,
            401: ErrorSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
        },
    )
    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        order = self.get_object()
        order.process()
        order.save()
        return Response(self.get_serializer(order).data)

    @extend_schema(
        description=(
            "Transition in_progress -> shipped.\n\n"
            "Invariants:\n"
            "- Order must be in IN_PROGRESS state.\n"
        ),
        responses={
            200: OrderSerializer,
            400: ErrorSerializer,
            401: ErrorSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
        },
    )
    @action(detail=True, methods=["post"])
    def mark_shipped(self, request, pk=None):
        order = self.get_object()
        order.ship()
        order.save()
        return Response(self.get_serializer(order).data)

    @extend_schema(
        description=(
            "Transition shipped -> completed.\n\n"
            "Invariants:\n"
            "- Order must be in SHIPPED state.\n"
        ),
        responses={
            200: OrderSerializer,
            400: ErrorSerializer,
            401: ErrorSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
            409: ErrorSerializer,
        },
    )
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        order = self.get_object()
        order.complete()
        order.save()
        return Response(self.get_serializer(order).data)

    @extend_schema(
        description=(
            "Transition any -> cancelled.\n\n"
            "Invariants:\n"
            "- Order must not be in COMPLETED state.\n"
        ),
        responses={
            200: OrderSerializer,
            400: ErrorSerializer,
            401: ErrorSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
            409: ErrorSerializer,
        },
    )
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        order.cancel()
        order.save()
        return Response(self.get_serializer(order).data)


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.select_related("quote", "product")
    serializer_class = OrderItemSerializer


@extend_schema_view(
    list=extend_schema(
        description=(
            "Payment entity.\n\n"
            "Represents a payment attempt for an Order.\n\n"
            "State machine:\n"
            "created -> pending -> completed\n"
            "pending -> failed\n"
            "completed -> refund_pending -> refunded\n"
            "any -> failed\n\n"
            "Payments enforce currency and terminal state constraints.\n"
        )
    )
)
@crud_schema(PaymentSerializer)
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("order").all().order_by("-created_at")
    serializer_class = PaymentSerializer

    @extend_schema(
        description=(
            "Create payment record.\n\n"
            "Idempotency:\n"
            "- Requires Idempotency-Key header.\n"
            "- Reusing the same key returns HTTP 409 and replays the original response body.\n\n"
            "Invariants:\n"
            "- Order must not be CANCELLED.\n"
            "- Payment currency must match order currency.\n"
        ),
        parameters=[
            OpenApiParameter(
                name="Idempotency-Key",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Unique key used to guarantee idempotent POST requests."
            ),
        ],
        responses={
            201: PaymentSerializer,
            409: OpenApiResponse(
                response=PaymentSerializer,
                description="Returned when the same Idempotency-Key was already used. Contains the original Payment representation."
            ),
            400: ErrorSerializer,
            401: ErrorSerializer,
            403: ErrorSerializer,
        },
    )
    @idempotency_key(optional=False)
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(
        description=(
            "Create payment record.\n\n"
            "Invariants:\n"
            "- Order must not be CANCELLED.\n"
            "- Payment currency must match order currency.\n"
        ),
        responses={
            200: PaymentSerializer,
            400: ErrorSerializer,
            401: ErrorSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
        },
    )
    @action(detail=True, methods=["post"])
    def create_payment(self, request, pk=None):
        payment = self.get_object()
        payment.save()
        return Response(self.get_serializer(payment).data)

    @extend_schema(
        description=(
            "Transition created -> pending.\n\n"
            "Invariants:\n"
            "- Payment must be in CREATED state.\n"
            "- Payment must not be in terminal state.\n"
        ),
        responses={
            200: PaymentSerializer,
            400: ErrorSerializer,
            401: ErrorSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
            409: ErrorSerializer,
        },
    )
    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        payment = self.get_object()
        payment.start_processing()
        payment.save()
        return Response(self.get_serializer(payment).data)

    @extend_schema(
        description=(
            "Transition pending -> completed.\n\n"
            "Invariants:\n"
            "- Payment must be in PENDING state.\n"
            "- Payment must not be in terminal state.\n"
        ),
        responses={
            200: PaymentSerializer,
            400: ErrorSerializer,
            401: ErrorSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
            409: ErrorSerializer,
        },
    )
    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        payment = self.get_object()
        payment.complete()
        payment.paid_at = timezone.now()
        payment.save()
        return Response(self.get_serializer(payment).data)

    @extend_schema(
        description=(
            "Transition completed -> refund_pending.\n\n"
            "Invariants:\n"
            "- Payment must be in COMPLETED state.\n"
            "- Payment must not be in terminal state.\n"
        ),
        responses={
            200: PaymentSerializer,
            400: ErrorSerializer,
            401: ErrorSerializer,
            403: ErrorSerializer,
            404: ErrorSerializer,
            409: ErrorSerializer,
        },
    )
    @action(detail=True, methods=["post"], url_path="refund")
    def request_refund(self, request, pk=None):
        payment = self.get_object()
        payment.request_refund()
        payment.save()
        return Response(self.get_serializer(payment).data)