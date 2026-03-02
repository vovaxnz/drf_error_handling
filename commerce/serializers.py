# commerce/serializers.py
from rest_framework import serializers

from .models.quotes import Quote
from .models.orders import Order, OrderItem
from .models.payments import Payment
from .models.quotes import QuoteItem

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_serializer

from .models.quotes import Quote
from .models.orders import Order
from .models.payments import Payment

@extend_schema_serializer(
    description=(
        "Quote invariants:\n"
        "- Items can be added only in draft state\n"
        "- Cannot send empty quote\n"
        "- Cannot modify accepted quote\n\n"
    )
)
class QuoteSerializer(serializers.ModelSerializer):
    available_transitions = serializers.SerializerMethodField()

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
            "available_transitions",
        ]
        read_only_fields = [
            "id",
            "total_amount",
            "created_at",
            "updated_at",
            "available_transitions",
        ]



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


@extend_schema_serializer(
    description=(
        "Order invariants:\n"
        "- Created only from accepted quote\n"
        "- Idempotency key unique per client\n"
        "- Currency must match quote\n"
        "- Cannot modify completed order\n"
        "- Confirm requires full payment\n\n"
    )
)
class OrderSerializer(serializers.ModelSerializer):
    available_transitions = serializers.SerializerMethodField()

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
            "available_transitions",
        ]
        read_only_fields = [
            "id",
            "status",
            "total_amount",
            "placed_at",
            "created_at",
            "available_transitions",
        ]

        extra_kwargs = {
            "idempotency_key": {
                "help_text": "Unique per client. Ensures idempotent creation."
            }
        }


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

@extend_schema_serializer(
    description=(
        "Payment invariants:\n"
        "- Currency must match Order.currency\n"
        "- Unique per provider + idempotency_key\n"
        "- Cannot modify payment in terminal state\n"
        "- Cannot create payment for cancelled order\n\n"
    )
)
class PaymentSerializer(serializers.ModelSerializer):
    available_transitions = serializers.SerializerMethodField()

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
            "available_transitions",
        ]
        read_only_fields = [
            "id",
            "status",
            "provider_reference",
            "paid_at",
            "created_at",
            "available_transitions",
        ]

        extra_kwargs = {
            "currency": {
                "help_text": "Must match order currency."
            },
            "idempotency_key": {
                "help_text": "Unique per provider."
            }
        }
