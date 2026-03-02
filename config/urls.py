# config/urls.py
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from drf_spectacular.views import (
    SpectacularJSONAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from catalog.views import ProductCategoryViewSet, ProductViewSet
from commerce.views import OrderItemViewSet, QuoteItemViewSet, QuoteViewSet, OrderViewSet, PaymentViewSet
from .router_constants import RoutePrefix

router = DefaultRouter()


router.register(RoutePrefix.PRODUCT_CATEGORIES, ProductCategoryViewSet, basename=RoutePrefix.PRODUCT_CATEGORIES)
router.register(RoutePrefix.PRODUCTS, ProductViewSet, basename=RoutePrefix.PRODUCTS)
router.register(RoutePrefix.QUOTES, QuoteViewSet, basename=RoutePrefix.QUOTES)
router.register(RoutePrefix.ORDERS, OrderViewSet, basename=RoutePrefix.ORDERS)
router.register(RoutePrefix.PAYMENTS, PaymentViewSet, basename=RoutePrefix.PAYMENTS)
router.register(RoutePrefix.QUOTE_ITEMS, QuoteItemViewSet, basename=RoutePrefix.QUOTE_ITEMS)
router.register(RoutePrefix.ORDER_ITEMS, OrderItemViewSet, basename=RoutePrefix.ORDER_ITEMS)

def root_redirect(request):
    return redirect("swagger-ui")

urlpatterns = [
    path("", root_redirect),
    path("api/v1/openapi.json", SpectacularJSONAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/v1/", include(router.urls)),
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("dj_rest_auth.urls")),
    path("api/v1/auth/registration/", include("dj_rest_auth.registration.urls")),
]