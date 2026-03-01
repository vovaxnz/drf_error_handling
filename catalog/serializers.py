# catalog/serializers.py
from rest_framework import serializers

from .models import ProductCategory, Product



class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ["id", "name", "parent"]
        read_only_fields = ["id"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "category",
            "title",
            "description",
            "sku",
            "product_url",
            "image_url",
            "price_amount",
            "price_currency",
            "attributes",
            "embedding_ref",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]