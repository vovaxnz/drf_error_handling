# commerce/views.py
from rest_framework import viewsets

from .models import Quote, QuoteItem, Order, OrderItem, Payment
from .serializers import (
    QuoteSerializer,
    QuoteItemSerializer,
    OrderSerializer,
    OrderItemSerializer,
    PaymentSerializer,
)


class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.select_related("client").all().order_by("-created_at")
    serializer_class = QuoteSerializer


class QuoteItemViewSet(viewsets.ModelViewSet):
    queryset = (
        QuoteItem.objects.select_related("quote", "product")
        .all()
        .order_by("-created_at")
    )
    serializer_class = QuoteItemSerializer


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.select_related("client", "quote").all().order_by("-created_at")
    serializer_class = OrderSerializer


class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.select_related("order", "product").all().order_by("-created_at")
    serializer_class = OrderItemSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("order").all().order_by("-created_at")
    serializer_class = PaymentSerializer