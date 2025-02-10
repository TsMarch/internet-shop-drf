import random

from django.core.management.base import BaseCommand
from django.db import transaction
from shop.models import (
    Product,
    ProductCategory,
    ProductRating,
    ProductReview,
    ReviewComment,
    ReviewCommentReply,
    User,
)


class Command(BaseCommand):
    help = "Генерирует тестовые данные: категория, продукты, отзывы, комментарии и ответы"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        category = ProductCategory.objects.create(name="tv")

        for i in range(10):
            old_price = random.randint(100, 5000)
            discount = random.randint(0, 50)
            price = old_price * (1 - discount / 100)
            available_quantity = random.randint(0, 100)

            Product.objects.create(
                category=category,
                name=f"Product {i + 1}",
                description=f"Description {i + 1}",
                old_price=old_price,
                discount=discount,
                price=price,
                available_quantity=available_quantity,
            )
        user = User.objects.first()
        products = list(Product.objects.all())

        for _ in range(20):
            product = random.choice(products)

            rating, created = ProductRating.objects.get_or_create(
                user=user, product=product, defaults={"rating": random.randint(1, 5)}
            )

            if not ProductReview.objects.filter(rating=rating).exists():
                review = ProductReview.objects.create(
                    product=product, user=user, text=f"Отзыв {random.randint(1, 1000)}", rating=rating
                )

                for _ in range(3):
                    comment = ReviewComment.objects.create(
                        review=review, user=user, text=f"Комментарий на отзыв {review.id}"
                    )

                    for _ in range(5):
                        ReviewCommentReply.objects.create(
                            review_comment=comment, user=user, text=f"Ответ на комментарий {comment.id}"
                        )
