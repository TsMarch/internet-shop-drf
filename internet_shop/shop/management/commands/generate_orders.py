import random
from datetime import date, datetime, timedelta

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

        users = list(User.objects.all())
        products = list(Product.objects.all())

        if not users:
            self.stderr.write("Ошибка: нет пользователей в базе данных.")
            return
        if not products:
            self.stderr.write("Ошибка: нет продуктов в базе данных.")
            return

        def random_date(start_date, end_date):
            if isinstance(start_date, date):
                start_date = datetime.combine(start_date, datetime.min.time())
            if isinstance(end_date, date):
                end_date = datetime.combine(end_date, datetime.min.time())

            time_delta = end_date - start_date
            random_days = random.randint(0, time_delta.days)
            return start_date + timedelta(days=random_days)

        with transaction.atomic():
            while orders_left > 0:
                orders_to_create = min(orders_left, batch_size)
                orders_left -= orders_to_create

                orders = []
                for _ in range(orders_to_create):
                    user = random.choice(users)

                    start_date = datetime(2024, 1, 1)
                    end_date = datetime.today()
                    order_date = random_date(start_date, end_date)

                    orders.append(Order(user=user, created_at=order_date))

                Order.objects.bulk_create(orders, batch_size=batch_size)

                created_orders = Order.objects.order_by("-id")[:orders_to_create]

                order_items = []
                for order in tqdm(created_orders, desc="Добавление товаров в заказы", leave=True):
                    num_items = random.randint(1, 5)
                    selected_products = random.sample(products, num_items)

                    for product in selected_products:
                        quantity = random.randint(1, 5)

                        order_items.append(
                            OrderItems(order=order, product=product, price=product.price, quantity=quantity)
                        )

                OrderItems.objects.bulk_create(order_items, batch_size=batch_size)
                print(f"Осталось заказов: {orders_left}")
