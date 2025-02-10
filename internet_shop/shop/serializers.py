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
    ProductRating,
    ProductReviewComment,
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
    average_rating = serializers.FloatField(read_only=True)
    rating_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = "__all__"


class ProductSerializer(ProductListSerializer, DynamicFieldsModelSerializer):
    comments = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = "__all__"

    def create(self, validated_data):
        old_price = validated_data.get("old_price")
        discount = validated_data.get("discount")

        if old_price is not None and discount is not None:
            validated_data["price"] = Decimal(old_price - old_price * discount / 100)
        else:
            validated_data["price"] = None

        return super().create(validated_data)

    def get_comments(self, obj):
        """Получаем только корневые отзывы (REVIEW) с привязкой к продукту"""
        reviews = ProductReviewComment.objects.filter(product=obj, type=ProductReviewComment.NodeType.REVIEW)
        return ProductReviewCommentSerializer(reviews, many=True).data


class ProductRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRating
        fields = "__all__"


class ProductReviewCommentSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()

    class Meta:
        model = ProductReviewComment
        fields = ["id", "user", "text", "type", "created_at", "updated_at", "children", "rating"]

    def get_children(self, obj):
        """Рекурсивно получаем все дочерние комментарии и ответы"""
        children = obj.children.all()
        return ProductReviewCommentSerializer(children, many=True).data if children else []

    def get_rating(self, obj):
        """Возвращает рейтинг только для отзывов"""
        return (
            ProductRatingSerializer(obj.rating).data
            if obj.type == ProductReviewComment.NodeType.REVIEW and obj.rating
            else None
        )


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


class UserBalanceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBalanceHistory
        fields = "__all__"
