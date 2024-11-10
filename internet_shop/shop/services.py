from decimal import Decimal

from rest_framework.exceptions import ValidationError

from .models import (
    CartItems,
    Order,
    OrderItems,
    Product,
    UserBalance,
    UserBalanceHistory,
)


class UserBalanceService:
    @staticmethod
    def create_balance_history(user_id, operation_type, amount):
        if operation_type not in [UserBalanceHistory.OperationType.DEPOSIT, UserBalanceHistory.OperationType.PAYMENT]:
            raise ValidationError("Неверный тип операции")
        UserBalanceHistory.objects.create(user=user_id, operation_type=operation_type, amount=amount)


class ProductService:
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


class OrderService:
    def __init__(self, user):
        self.user = user

    def create_order(self):
        cart_items = CartItems.objects.filter(cart__user=self.user)
        user_balance = UserBalance.objects.get(user=self.user)
        order = Order.objects.create(user=self.user)
        try:
            order_items, order_sum, updated_products = ProductService.product_balance(order, cart_items)
        except ValueError:
            raise ValidationError("no items were updated")
        match user_balance.balance >= order_sum:
            case True:
                user_balance.balance -= order_sum
                Product.objects.bulk_update(updated_products, ["available_quantity"])
                user_balance.save()
                UserBalanceService.create_balance_history(
                    self.user, UserBalanceHistory.OperationType.PAYMENT, order_sum
                )
                OrderItems.objects.bulk_create(order_items)
                cart_items.delete()
                return order
            case False:
                raise ValidationError("not enough money")
