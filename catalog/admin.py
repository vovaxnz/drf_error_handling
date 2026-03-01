# catalog/admin.py
from django.contrib import admin

from .models import ProductCategory, Product


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent")
    search_fields = ("name", "parent__name")
    autocomplete_fields = ("parent",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "sku", "price_amount", "price_currency", "is_active", "updated_at")
    list_filter = ("is_active", "price_currency", "category")
    search_fields = ("title", "sku")
    autocomplete_fields = ("category",)
    readonly_fields = ("created_at", "updated_at")