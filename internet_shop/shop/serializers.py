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


class ProductSerializerMixin:
    def get_serializer_class(self):
        match self.action:
            case 'retrieve':
                return ProductSerializer
            case _:
                return ProductListSerializer
