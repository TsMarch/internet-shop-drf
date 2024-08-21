from django.contrib import admin
from django.urls import include, path
from rest_framework import routers

from .views import CartViewSet, ProductViewSet

shop_router = routers.DefaultRouter()
shop_router.register("", ProductViewSet, basename="product")
cart_router = routers.DefaultRouter()
cart_router.register(r"", CartViewSet, basename="cart")

urlpatterns = [path("product/", include(shop_router.urls)), path("cart/", include(cart_router.urls))]
