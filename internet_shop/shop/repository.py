from abc import ABC, abstractmethod
from typing import List

from django.db import transaction

from internet_shop.shop.models import Product


class ProductRepositoryInterface(ABC):
    @abstractmethod
    def bulk_insert(self, products: List[Product]):
        pass


class ProductRepository(ProductRepositoryInterface):
    @staticmethod
    @transaction.atomic
    def bulk_insert(products: List[Product]):
        if products:
            Product.objects.bulk_create(products)
