from abc import ABC, abstractmethod
from decimal import Decimal

from rest_framework.exceptions import ValidationError

from .models import (
    Cart,
    CartItems,
    Order,
    OrderItems,
    Product,
    UserBalance,
    UserBalanceHistory,
)


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


class ProductService(ABC):
    @abstractmethod
    def validate_quantity(self):
        pass


class CartProductService(ProductService):
    def __init__(self, products_id: list[int]):
        self.product = Product.objects.filter(id__in=products_id)

    def validate_quantity(self):
        pass


class OrderProductService(ProductService):
    def __init__(self, order_data: list[CartItems], order: Order):
        self.products = Product.objects.filter(id__in=[product.product_id for product in order_data])
        self.order_data = order_data
        self.order = order

    @staticmethod
    def count_total_sum(order_items):
        total_sum = 0
        for item in order_items:
            total_sum += item.quantity * item.price
        return total_sum

    def validate_quantity(self):
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
    def __init__(self, cart: Cart, product_id: int):
        self.cart = cart
        self.product_id = product_id

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
        self.cart_items = CartItems.objects.filter(cart__user=user)
        self.order = Order.objects.create(user=self.user)
        self.products_processor = OrderProductService(self.cart_items, order=self.order)

    def create_order(self):
        user_balance = UserBalance.objects.get(user=self.user)
        if not self.cart_items:
            raise ValidationError("empty cart")
        order_items, updated_products = self.products_processor.validate_quantity()
        order_sum = self.products_processor.count_total_sum(order_items)

        if user_balance.balance >= order_sum:
            user_balance.balance -= order_sum
            Product.objects.bulk_update(updated_products, ["available_quantity"])
            user_balance.save()
            OrderItems.objects.bulk_create(order_items)
            self.cart_items.delete()
            self.order.total_sum = order_sum
            self.order.save()
            self.payment_processor.create_balance_history(self.user, order_sum)
            return self.order

        raise ValidationError("not enough money")
