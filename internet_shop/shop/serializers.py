from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.response import Response

from .models import Product, Cart, CartItems


class DynamicFieldsModelSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        print(kwargs)
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)
        ##
        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class ProductSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"


class ProductLimitedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        exclude = ["description", "available", "category", "old_price", "discount"]


class ProductCreateSerializer(ProductSerializer):
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
                return ProductSerializer
            case "create":
                return ProductCreateSerializer
            case _:
                return ProductSerializer

    def list(self, request, *args, **kwargs):
        queryset = Product.objects.all()
        serializer = ProductSerializer(queryset, many=True, fields=["id", "name", "price"])
        return Response(serializer.data)

    def retrieve(self, request, pk=None, *args, **kwargs):
        queryset = Product.objects.all()
        product = get_object_or_404(queryset, pk=pk)
        serializer = ProductSerializer(product)
        return Response(serializer.data)


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductLimitedSerializer()

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
