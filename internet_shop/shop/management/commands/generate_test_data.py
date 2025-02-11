import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from shop.models import Product, ProductCategory, ProductReviewComment, User


class Command(BaseCommand):
    help = "Генерирует тестовые данные: категория, продукты, отзывы и комментарии"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        superuser = User.objects.first()
        category = ProductCategory.objects.create(name="TV")
        products = []
        for i in range(10):
            old_price = random.randint(100, 5000)
            discount = random.randint(0, 50)
            price = Decimal(old_price - old_price * discount / 100)
            available_quantity = random.randint(0, 100)

            product = Product.objects.create(
                category=category,
                name=f"Product {i + 1}",
                description=f"Description {i + 1}",
                old_price=old_price,
                discount=discount,
                price=price,
                available_quantity=available_quantity,
            )
            products.append(product)

        for _ in range(50):
            product = random.choice(products)

            review = ProductReviewComment.objects.create(
                product=product,
                user=superuser,
                text=f"Отзыв {random.randint(1, 1000)}",
                rating=random.randint(1, 5),
            )

            for _ in range(10):
                comment = ProductReviewComment.objects.create(
                    product=product,
                    user=superuser,
                    text=f"Комментарий на отзыв {review.id}",
                    parent=review,
                )

                for _ in range(10):
                    ProductReviewComment.objects.create(
                        product=product,
                        user=superuser,
                        text=f"Ответ на комментарий {comment.id}",
                        parent=comment,
                    )
