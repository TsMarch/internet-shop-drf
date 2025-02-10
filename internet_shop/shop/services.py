from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Literal

import pandas as pd
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from eav.models import Attribute, Value
from rest_framework.exceptions import ValidationError

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

DATATYPE_MAP = {
    "int": Attribute.TYPE_INT,
    "float": Attribute.TYPE_FLOAT,
    "text": Attribute.TYPE_TEXT,
    "date": Attribute.TYPE_DATE,
    "bool": Attribute.TYPE_BOOLEAN,
    "object": Attribute.TYPE_OBJECT,
    "enum": Attribute.TYPE_ENUM,
    "json": Attribute.TYPE_JSON,
    "csv": Attribute.TYPE_CSV,
}


class ProductReviewCreateService:
    def __init__(self, product_id, user):
        self.product = Product.objects.get(id=product_id)
        self.user = user

    def has_purchased_product(self):
        if not Order.objects.filter(user=self.user, products=self.product).exists():
            return ValidationError({"error": "товар не приобретен"})

    def get_rating(self, rating_value=None):
        rating = ProductRating.objects.filter(user=self.user, product=self.product).first()

        if not rating:
            if rating_value is None:
                raise ValidationError({"error": "необходимо указать рейтинг"})
            rating = ProductRating.objects.create(user=self.user, product=self.product, rating=rating_value)
        return rating

    def create_review(self, text, rating_value):
        self.has_purchased_product()
        rating = self.get_rating(rating_value)
        review = ProductReviewComment.objects.create(
            product=self.product, user=self.user, text=text, type=ProductReviewComment.NodeType.REVIEW, rating=rating
        )
        return review


class ProductAttributeService:
    def __init__(self, product_id, attributes):
        self.product = Product.objects.get(id=product_id)
        self.attributes = attributes

    def attach_attribute(self):
        for attr in self.attributes:
            setattr(self.product.eav, attr, self.attributes[attr][0])
        self.product.save()
        return self.product


class AttributeService:
    def __init__(self, attributes: list):
        self.attributes = {attr["attribute_name"]: (attr["attribute_value"], attr["datatype"]) for attr in attributes}

    def resolve_attributes(self):
        existing_attributes = Attribute.objects.filter(name__in=self.attributes.keys()).values_list("name", flat=True)
        attributes_to_create = [
            Attribute(name=name, datatype=DATATYPE_MAP[data[1]], slug=name)
            for name, data in self.attributes.items()
            if name not in existing_attributes
        ]
        if attributes_to_create:
            Attribute.objects.bulk_create(attributes_to_create)

        return self.attributes

    @staticmethod
    def delete_attribute(product_id, attribute_name):
        Value.objects.filter(entity_id=product_id, attribute__name=attribute_name).delete()


class UserBalanceProcessorInterface(ABC):
    @abstractmethod
    def create_balance_history(self, user_id, amount):
        pass


class PaymentProcessor(UserBalanceProcessorInterface):
    def create_balance_history(self, user_id, amount):
        UserBalanceHistory.objects.create(
            user=user_id, operation_type=UserBalanceHistory.OperationType.PAYMENT, amount=amount
        )


class DepositProcessor(UserBalanceProcessorInterface):
    def create_balance_history(self, user_id, amount):
        UserBalanceHistory.objects.create(
            user=user_id, operation_type=UserBalanceHistory.OperationType.DEPOSIT, amount=amount
        )


class ProductFileService:
    def __init__(self, data: UploadedFile):
        self.data = pd.read_excel(data).to_dict(orient="records")

    def create_products(self):
        category_names = {product.get("category") for product in self.data}
        categories = ProductCategory.objects.filter(name__in=category_names)
        category_cache = {category.name: category for category in categories}
        products = []

        for product in self.data:
            category = category_cache.get(product.get("category"))
            old_price = product.get("price")
            discount = product.get("discount")
            if old_price is not None and discount is not None:
                product["price"] = Decimal(old_price - old_price * discount / 100)
            else:
                product["price"] = None
            products.append(
                Product(
                    name=product.get("name"),
                    old_price=old_price,
                    available_quantity=product.get("available_quantity"),
                    category=category,
                    description=product.get("description", "default"),
                    discount=discount,
                    price=product["price"],
                )
            )
        Product.objects.bulk_create(products)


class ProductService:
    def __init__(
        self,
        product_id: int,
        field: Literal[
            "category", "name", "description", "old_price", "discount", "price", "available", "available_quantity"
        ],
    ):
        self.product = Product.objects.get(id=product_id)
        self.field = field

    def update_field(self, field_value: int | str) -> Product:
        setattr(self.product, self.field, field_value)
        self.product.save()
        return self.product


class OrderItemsService(ABC):
    @abstractmethod
    def validate_quantity(self):
        pass


class ExternalOrderItemsService(OrderItemsService):
    def __init__(self, order_data: list[CartItems]):
        self.products = Product.objects.filter(id__in=[product.product_id for product in order_data])
        self.order_data = order_data

    def validate_quantity(self) -> list[Product]:
        updated_products = []
        for product, order_item in zip(self.products, self.order_data):
            if product.available_quantity == 0:
                continue
            order_item.quantity = min(product.available_quantity, order_item.quantity)
            product.available_quantity -= order_item.quantity
            updated_products.append(product)
        Product.objects.bulk_update(updated_products, ["available_quantity"])
        return updated_products


class InternalOrderItemsService(OrderItemsService):
    def __init__(self, order_data: list[CartItems], order: Order):
        self.products = Product.objects.filter(id__in=[product.product_id for product in order_data])
        self.order_data = order_data
        self.order = order

    @staticmethod
    def count_total_sum(order_items) -> Decimal:
        total_sum = 0
        for item in order_items:
            total_sum += item.quantity * item.price
        return Decimal(total_sum)

    def validate_quantity(self) -> tuple[list[OrderItems], list[Product]]:
        updated_products = []
        order_items = []
        for product, order_item in zip(self.products, self.order_data):
            if product.available_quantity == 0:
                continue
            order_item.quantity = min(product.available_quantity, order_item.quantity)
            product.available_quantity -= order_item.quantity
            updated_products.append(product)
            order_items.append(
                OrderItems(
                    order=self.order,
                    price=Decimal(order_item.price),
                    product_id=order_item.product_id,
                    quantity=order_item.quantity,
                )
            )
        return order_items, updated_products


class CartItemsService:
    @staticmethod
    def validate_quantity(requested_quantity: int, cart: Cart, product_id: int):
        print(cart, product_id)
        cart_item = CartItems.objects.get(cart=cart, product=product_id)
        product = Product.objects.get(pk=product_id)
        if product.available_quantity == 0:
            raise ValueError("not enough product")
        cart_item.quantity = min(product.available_quantity, requested_quantity)
        cart_item.price = product.price
        cart_item.save()
        return cart


class OrderService:
    def __init__(self, user, payment_processor: UserBalanceProcessorInterface):
        self.user = user
        self.payment_processor = payment_processor
        self.order = Order.objects.create(user=self.user)

    @transaction.atomic
    def create_order(self) -> Order | ValidationError:
        cart_items = CartItems.objects.select_for_update().filter(cart__user=self.user)

        if not cart_items:
            raise ValidationError("empty cart")

        products_processor = InternalOrderItemsService(cart_items, order=self.order)
        user_balance = UserBalance.objects.select_for_update().get(user=self.user)
        Product.objects.select_for_update().filter(cartitems__cart__user=self.user)
        order_items, updated_products = products_processor.validate_quantity()
        order_sum = products_processor.count_total_sum(order_items)
        if user_balance.balance >= order_sum:
            user_balance.balance -= order_sum
            Product.objects.bulk_update(updated_products, ["available_quantity"])
            user_balance.save()
            OrderItems.objects.bulk_create(order_items)
            cart_items.delete()
            self.order.total_sum = Decimal(order_sum)
            self.order.save()
            self.payment_processor.create_balance_history(self.user, order_sum)
            return self.order

        raise ValidationError("not enough money")
