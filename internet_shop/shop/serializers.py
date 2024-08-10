from rest_framework import serializers
from .models import Product


class ProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "price", "old_price"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"

    def create(self, product):
        print(product)
        old_price = product.get("old_price")
        discount = product.get("discount")
        match all([old_price is not None, discount is not None]):
            case True:
                product["price"] = old_price - old_price * discount / 100
            case _:
                product["price"] = None
        return super().create(product)


class ProductSerializerMixin:
    def get_serializer_class(self):
        match self.action:
            case "retrieve":
                return ProductSerializer
            case "list":
                return ProductListSerializer
            case "create":
                return ProductSerializer
            case _:
                return ProductListSerializer
