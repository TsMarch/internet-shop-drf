from typing import List

from django.db import transaction

from internet_shop.shop.models import Product


class ProductRepository:
    @staticmethod
    @transaction.atomic
    def bulk_insert(products: List[Product]):
        if products:
            Product.objects.bulk_create(products)
