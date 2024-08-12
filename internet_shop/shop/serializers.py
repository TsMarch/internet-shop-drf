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


class ProductInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        exclude = ["description", "available", "category", "old_price", "discount"]


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductInfoSerializer()

    class Meta:
        model = CartItems
        fields = ["product", "quantity", "added_at"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True)

    class Meta:
        model = Cart
        fields = ["id", "user", "items"]

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        cart = Cart.objects.create(**validated_data)
        for item_data in items_data:
            CartItems.objects.create(cart=cart, **item_data)
        return cart


class CartSerializerMixin:
    def get_serializer_class(self):
        match self.action:
            case "create":
                return CartSerializer
            case _:
                return CartSerializer
