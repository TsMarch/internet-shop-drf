from django.urls import include, path
from rest_framework import routers

from .views import (
    CartViewSet,
    ExternalOrderViewSet,
    OrderViewSet,
    ProductCategoryViewSet,
    ProductViewSet,
    ReviewCommentViewSet,
    SalesStatisticsViewSet,
    UserBalanceViewSet,
    UserRegistrationViewSet,
    delete_attribute,
)

shop_router = routers.DefaultRouter()
shop_router.register("", ProductViewSet, basename="product")
category_router = routers.DefaultRouter()
category_router.register("", ProductCategoryViewSet, basename="category")
cart_router = routers.DefaultRouter()
cart_router.register(r"", CartViewSet, basename="cart")
order_router = routers.DefaultRouter()
order_router.register(r"", OrderViewSet, basename="orders")
registration_router = routers.DefaultRouter()
registration_router.register(r"", UserRegistrationViewSet, basename="registration")
user_balance_router = routers.DefaultRouter()
user_balance_router.register(r"", UserBalanceViewSet, basename="balance")
external_order_router = routers.DefaultRouter()
external_order_router.register(r"", ExternalOrderViewSet, basename="external-orders")
review_comment_router = routers.DefaultRouter()
review_comment_router.register(r"", ReviewCommentViewSet, basename="reviews-comments")


urlpatterns = [
    path("product/", include(shop_router.urls)),
    path(
        "product/<int:pk>/comments/<int:comment_id>/",
        ProductViewSet.as_view({"get": "comments"}),
        name="product-comments",
    ),
    path("product_category/", include(category_router.urls)),
    path("cart/", include(cart_router.urls)),
    path("orders/", include(order_router.urls)),
    path("registration/", include(registration_router.urls)),
    path("balance/", include(user_balance_router.urls)),
    path("external/", include(external_order_router.urls)),
    path("delete_attribute/", delete_attribute),
    path("review-comment/", include(review_comment_router.urls)),
    path("sales/statistics/", SalesStatisticsViewSet.as_view(), name="sales-statistics"),
]
