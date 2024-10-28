from django.urls import include, path
from rest_framework import routers

from .views import CartViewSet, OrderViewSet, ProductViewSet, UserRegistrationViewSet

shop_router = routers.DefaultRouter()
shop_router.register("", ProductViewSet, basename="product")
cart_router = routers.DefaultRouter()
cart_router.register(r"", CartViewSet, basename="cart")
order_router = routers.DefaultRouter()
order_router.register(r"", OrderViewSet, basename="orders")
registration_router = routers.DefaultRouter()
registration_router.register(r"", UserRegistrationViewSet, basename="registration")

urlpatterns = [
    path("product/", include(shop_router.urls)),
    path("cart/", include(cart_router.urls)),
    path("orders/", include(order_router.urls)),
    path("registration/", include(registration_router.urls)),
]
