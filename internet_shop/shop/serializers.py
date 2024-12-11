from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    Cart,
    CartItems,
    Order,
    OrderItems,
    Product,
    ProductCategory,
    UserBalance,
    UserBalanceHistory,
)

User = get_user_model()


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = ProductCategory
        fields = "__all__"


class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"], email=validated_data["email"], password=validated_data["password"]
        )
        return user


class ProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    attributes = serializers.DictField(source="eav.get_values_dict", read_only=True)

    class Meta:
        model = Product
        fields = "__all__"


class ProductSerializer(DynamicFieldsModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    attributes = serializers.DictField(source="eav.get_values_dict", read_only=True)

    class Meta:
        model = Product
        fields = "__all__"

    def create(self, validated_data):
        old_price = validated_data.get("old_price")
        discount = validated_data.get("discount")
        match all([old_price is not None, discount is not None]):
            case True:
                validated_data["price"] = Decimal(old_price - old_price * discount / 100)
            case _:
                validated_data["price"] = None
        return super().create(validated_data)


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", required=False)
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    product_price = serializers.IntegerField(source="product.price", required=False)
    product_available_quantity = serializers.IntegerField(source="product.available_quantity", required=False)

    class Meta:
        model = CartItems
        fields = [
            "product_name",
            "product_id",
            "product_price",
            "product_available_quantity",
            "quantity",
            "added_at",
        ]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True)

    class Meta:
        model = Cart
        fields = ["id", "user", "items"]


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", required=False)
    product_id = serializers.IntegerField(source="product.id")
    product_price = serializers.IntegerField(source="price", required=False)
    product_quantity = serializers.IntegerField(source="quantity", required=False)

    class Meta:
        model = OrderItems
        fields = ["product_name", "product_id", "product_price", "product_quantity"]


class OrderSerializer(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = ["created_at", "total_sum"]


class OrderDetailSerializer(serializers.ModelSerializer):
    orderitems = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ["created_at", "total_sum", "orderitems"]


class UserBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBalance
        fields = "__all__"

    def create(self, validated_data):
        print(**validated_data)


class UserBalanceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBalanceHistory
        fields = "__all__"
