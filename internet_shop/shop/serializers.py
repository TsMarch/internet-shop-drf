from rest_framework import serializers
from .models import Cart, CartItems, Product, Order, OrderItems


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class ProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ["id", "name", "price", "old_price"]


class ProductSerializer(DynamicFieldsModelSerializer):
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


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", required=False)
    product_id = serializers.IntegerField(source="product.id")
    product_price = serializers.IntegerField(source="product.price", required=False)
    product_available_quantity = serializers.IntegerField(source="product.available_quantity", required=False)

    class Meta:
        model = CartItems
        fields = ["product_name", "product_id", "product_price", "product_available_quantity", "quantity", "added_at"]


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True)

    class Meta:
        model = Cart
        fields = ["id", "user", "items"]


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", required=False)
    product_id = serializers.IntegerField(source="product.id")
    product_price = serializers.IntegerField(source="price", required=False)
    product_quantity = serializers.IntegerField(source='quantity', required=False)

    class Meta:
        model = OrderItems
        fields = ["product_name", "product_id", "product_price", 'quantity']


class OrderSerializer(serializers.ModelSerializer):
    orderitems = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = "__all__"
