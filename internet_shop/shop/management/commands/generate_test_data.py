import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from shop.models import Product, ProductCategory
from tqdm import tqdm

from .services import categories_inp, products_inp


class Command(BaseCommand):
    help = "Generate test data for products and reviews"

    def handle(self, *args, **kwargs):
        categories = [ProductCategory.objects.create(name=f"{i}") for i in categories_inp]

        nested_categories = [
            ProductCategory.objects.create(name=f"{categories_inp[i.name]}", parent=i) for i in categories
        ]

        batch_size = 1000000
        total_products = 10000000
        products_left = total_products

        categories += nested_categories

        with transaction.atomic():
            while products_left > 0:
                products_to_create = min(products_left, batch_size)
                products_left -= products_to_create

                products = []
                for _ in range(products_to_create):
                    category = random.choice(categories)
                    category_name = category.name
                    product_name = random.choice(products_inp[category_name])  # случайный товар из выбранной категории
                    old_price = random.randint(100, 5000)
                    discount = random.randint(0, 50)
                    price = Decimal(old_price - old_price * discount / 100)
                    available_quantity = random.randint(0, 100)

                    product = Product(
                        category=category,
                        name=product_name,
                        description=f"Описание товара {product_name}",
                        old_price=old_price,
                        discount=discount,
                        price=price,
                        available_quantity=available_quantity,
                    )
                    products.append(product)

                for _ in tqdm(range(0, len(products), batch_size), desc="Добавление товаров", leave=True):
                    Product.objects.bulk_create(products, batch_size=batch_size)

                print(f"Осталось товаров: {products_left}")
