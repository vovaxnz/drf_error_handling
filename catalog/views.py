# catalog/views.py
from rest_framework import viewsets

from .models import ProductCategory, Product
from .serializers import (
    ProductCategorySerializer,
    ProductSerializer,
)


class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.select_related("parent").all().order_by("name")
    serializer_class = ProductCategorySerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = (
        Product.objects.select_related("category")
        .all()
        .order_by("-created_at")
    )
    serializer_class = ProductSerializer