# catalog/views.py
from rest_framework import viewsets

from common.serializers import ErrorSerializer, crud_schema

from .models import ProductCategory, Product
from .serializers import (
    ProductCategorySerializer,
    ProductSerializer,
)

from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiTypes,
    OpenApiResponse,
    extend_schema_view,
)

@crud_schema(ProductCategorySerializer)
class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.select_related("parent").all().order_by("name")
    serializer_class = ProductCategorySerializer


@extend_schema_view(
    retrieve=extend_schema(
        description=(
            "Retrieve product.\n\n"
            "Supports HTTP conditional requests using ETag.\n"
            "- Response includes ETag header.\n"
            "- Client may send If-None-Match header.\n"
            "- The If-None-Match value must be sent exactly as received, including the surrounding double quotes.\n"
            "- If ETag matches, server returns 304 Not Modified with empty body.\n"
        ),
        parameters=[
            OpenApiParameter(
                name="If-None-Match",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=False,
                description="ETag value previously returned by the server."
            ),
        ],
        responses={
            200: ProductSerializer,
            304: OpenApiResponse(
                description="Not Modified. Returned when If-None-Match matches current ETag."
            ),
            401: OpenApiResponse(response=ErrorSerializer),
            403: OpenApiResponse(response=ErrorSerializer),
            404: OpenApiResponse(response=ErrorSerializer),
        },
    )
)
@crud_schema(ProductSerializer)
class ProductViewSet(viewsets.ModelViewSet):


    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


    queryset = (
        Product.objects.select_related("category")
        .all()
        .order_by("-created_at")
    )
    serializer_class = ProductSerializer