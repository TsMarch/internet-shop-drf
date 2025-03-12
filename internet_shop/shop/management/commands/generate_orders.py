import random

from django.core.management.base import BaseCommand
from django.db import transaction
from shop.models import Order, OrderItems, Product, User
from tqdm import tqdm


class Command(BaseCommand):
    help = "Generate test data for orders and order items"

    def handle(self, *args, **kwargs):
        batch_size = 10000
        total_orders = 100000
        orders_left = total_orders

        with transaction.atomic():
            while orders_left > 0:
                orders_to_create = min(orders_left, batch_size)
                orders_left -= orders_to_create

                orders = [Order(user=User.objects.order_by("?").first()) for _ in range(orders_to_create)]
                Order.objects.bulk_create(orders, batch_size=batch_size)

                created_orders = Order.objects.order_by("-id")[:orders_to_create]

                order_items = []
                for order in tqdm(created_orders, desc="Добавление товаров в заказы", leave=True):
                    num_items = random.randint(1, 5)
                    product_ids = Product.objects.order_by("?").values_list("id", flat=True)[:num_items]

                    for product_id in product_ids:
                        product = Product.objects.filter(id=product_id).only("price").first()
                        if product:
                            quantity = random.randint(1, 5)
                            order_items.append(
                                OrderItems(order=order, product=product, price=product.price, quantity=quantity)
                            )

                OrderItems.objects.bulk_create(order_items, batch_size=batch_size)
                print(f"Осталось заказов: {orders_left}")
