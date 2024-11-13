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

    @staticmethod
    def product_balance(order, order_data: list[CartItems]) -> tuple[list[OrderItems], int, list]:
        products = Product.objects.filter(id__in=[product.product_id for product in order_data])
        updated_products = []
        order_sum = 0
        order_items = []
        for product, order_item in zip(products, order_data):
            if product.available_quantity == 0:
                continue
            order_item.quantity = min(product.available_quantity, order_item.quantity)
            order_sum += order_item.quantity * product.price
            product.available_quantity -= order_item.quantity
            updated_products.append(product)
            order_items.append(
                OrderItems(
                    order=order,
                    price=Decimal(order_item.price),
                    product_id=order_item.product_id,
                    quantity=order_item.quantity,
                )
            )
        if updated_products:
            return order_items, order_sum, updated_products
        else:
            raise ValueError

    def create_order(self):
        cart_items = CartItems.objects.filter(cart__user=self.user)
        user_balance = UserBalance.objects.get(user=self.user)
        order = Order.objects.create(user=self.user)
        try:
            order_items, order_sum, updated_products = self.product_balance(order, cart_items)
        except ValueError:
            raise ValidationError("no items were updated")

        if user_balance.balance >= order_sum:
            user_balance.balance -= order_sum
            Product.objects.bulk_update(updated_products, ["available_quantity"])
            user_balance.save()
            OrderItems.objects.bulk_create(order_items)
            cart_items.delete()
            self.payment_processor.create_balance_history(self.user, order_sum)
            return order

        raise ValidationError("not enough money")
