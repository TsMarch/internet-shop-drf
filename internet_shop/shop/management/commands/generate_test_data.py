import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from shop.models import Product, ProductCategory, ReviewComment, User


class Command(BaseCommand):
    help = "Generate test data for products and reviews"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        superuser = User.objects.first()
        category = ProductCategory.objects.create(name="TV")

        products = [
            Product.objects.create(
                category=category,
                name=f"Product {i + 1}",
                description=f"Description {i + 1}",
                old_price=(old_price := random.randint(100, 5000)),
                discount=(discount := random.randint(0, 50)),
                price=Decimal(old_price - old_price * discount / 100),
                available_quantity=random.randint(0, 100),
            )
            for i in range(10)
        ]

        reviews = [
            ReviewComment.objects.create(
                product=random.choice(products),
                user=superuser,
                text=f"Отзыв {random.randint(1, 1000)}",
                rating=random.randint(1, 5),
            )
            for _ in range(50)
        ]

        comments = []
        for review in reviews:
            for _ in range(20):
                comment = ReviewComment.objects.create(
                    product=review.product,
                    user=superuser,
                    text=f"Комментарий на отзыв {review.id}",
                    parent=review,
                )
                comments.append(comment)

        for comment in comments:
            for _ in range(20):
                ReviewComment.objects.create(
                    product=comment.product,
                    user=superuser,
                    text=f"Ответ на комментарий {comment.id}",
                    parent=comment,
                )
