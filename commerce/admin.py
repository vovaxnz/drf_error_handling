# commerce/admin.py
from django.contrib import admin

from .models.quotes import Quote, QuoteItem
from .models.orders import Order, OrderItem
from .models.payments import Payment


class QuoteItemInline(admin.TabularInline):
    model = QuoteItem
    extra = 0
    autocomplete_fields = ("product",)
    readonly_fields = ("created_at",)


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("id", "client","status", "currency", "total_amount", "created_at", "updated_at")
    list_filter = ("status", "currency")
    search_fields = ("id", "client__email", "client__username")
    autocomplete_fields = ("client",)
    readonly_fields = ("total_amount", "created_at", "updated_at")
    inlines = (QuoteItemInline,)


@admin.register(QuoteItem)
class QuoteItemAdmin(admin.ModelAdmin):
    list_display = ("id", "quote", "product", "quantity", "unit_price", "currency", "created_at")
    list_filter = ("currency",)
    search_fields = ("id", "quote__id", "product__title", "product__sku")
    autocomplete_fields = ("quote", "product")
    readonly_fields = ("created_at",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ("product",)
    readonly_fields = ("created_at",)


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ("created_at", "paid_at")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "status", "currency", "total_amount", "idempotency_key", "placed_at", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("id", "client__email", "client__username", "idempotency_key", "quote__id")
    autocomplete_fields = ("client", "quote")
    readonly_fields = ("status", "total_amount", "placed_at", "created_at")
    inlines = (OrderItemInline, PaymentInline)


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "sku", "product_title", "quantity", "unit_price", "currency", "created_at")
    list_filter = ("currency", )
    search_fields = ("id", "order__id", "sku", "product_title")
    autocomplete_fields = ("order", "product")
    readonly_fields = ("created_at",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "status", "amount", "currency", "provider", "provider_reference", "paid_at", "created_at")
    list_filter = ("status", "currency", "provider")
    search_fields = ("id", "order__id", "provider_reference", "idempotency_key")
    autocomplete_fields = ("order",)
    readonly_fields = ("status", "provider_reference", "paid_at", "created_at")