# commerce/serializers.py
from rest_framework import serializers

from .models import Quote, QuoteItem, Order, OrderItem, Payment


class QuoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = [
            "id",
            "client",
            "status",
            "currency",
            "total_amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "total_amount", "created_at", "updated_at"]


class QuoteItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteItem
        fields = [
            "id",
            "quote",
            "product",
            "quantity",
            "unit_price",
            "currency",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = [
            "id",
            "client",
            "quote",
            "status",
            "currency",
            "total_amount",
            "shipping_address",
            "idempotency_key",
            "placed_at",
            "created_at",
        ]
        read_only_fields = ["id", "status", "total_amount", "placed_at", "created_at"]


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id",
            "order",
            "product",
            "quantity",
            "unit_price",
            "currency",
            "product_title",
            "sku",
            "product_url",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "order",
            "status",
            "amount",
            "currency",
            "provider",
            "provider_reference",
            "paid_at",
            "idempotency_key",
            "created_at",
        ]
        read_only_fields = ["id", "status", "provider_reference", "paid_at", "created_at"]