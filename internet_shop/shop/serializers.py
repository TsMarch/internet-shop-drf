from rest_framework import serializers
from rest_framework.relations import PrimaryKeyRelatedField

from .models import Product, Cart, CartItems


class ProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "price", "old_price"]


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"

    def create(self, validated_data):
        old_price = validated_data.get("old_price")
        discount = validated_data.get("discount")
        match all([old_price is not None, discount is not None]):
            case True:
                validated_data["price"] = old_price - old_price * discount / 100
            case _:
                validated_data["price"] = None
        return super().create(validated_data)


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


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItems
        fields = ["product", "quantity", "added_at"]
        depth = 1

    def validate_quantity(self, cart):
        quantity = cart.get('quantity')
        match quantity <= 0:
            case True:
                raise serializers.ValidationError("Quantity must be greater than 0.")
            case _:
                return quantity


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True)

    class Meta:
        model = Cart
        fields = ['id', 'items']


class CartSerializerMixin:
    pass
