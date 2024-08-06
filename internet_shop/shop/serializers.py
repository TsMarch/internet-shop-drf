from rest_framework import serializers
from .models import Product


class ProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["name", "price", "old_price"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class PriceValidator:
    def validate(self, product):
        return product.old_price - product.old_price * product.discount / 100
