import random

from django.core.management.base import BaseCommand
from django.db import transaction
from shop.models import (
    Product,
    ProductCategory,
    ProductRating,
    ProductReviewComment,
    User,
)


class Command(BaseCommand):
    help = "Генерирует тестовые данные: категории, продукты, отзывы, комментарии и ответы"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        category = ProductCategory.objects.create(name="TV")

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

            # Проверяем, есть ли уже рейтинг для данного пользователя и продукта
            rating, created = ProductRating.objects.get_or_create(
                user=user, product=product, defaults={"rating": random.randint(1, 5)}
            )

            # Если рейтинг уже существовал, обновим его случайным значением
            if not created:
                rating.rating = random.randint(1, 5)
                rating.save(update_fields=["rating"])

            # Проверяем, есть ли уже отзыв с этим рейтингом
            review = ProductReviewComment.objects.filter(rating=rating).first()

            # Если такого отзыва нет, создаем новый
            if not review:
                review = ProductReviewComment.objects.create(
                    product=product,
                    user=user,
                    text=f"Отзыв {random.randint(1, 1000)}",
                    type=ProductReviewComment.NodeType.REVIEW,
                    rating=rating,
                )

            # Создаем 3 комментария к каждому отзыву
            for _ in range(3):
                comment = ProductReviewComment.objects.create(
                    product=product,
                    user=user,
                    text=f"Комментарий на отзыв {review.id}",
                    type=ProductReviewComment.NodeType.COMMENT,
                    parent=review,
                )

                # Создаем 5 ответов на каждый комментарий
                for _ in range(5):
                    ProductReviewComment.objects.create(
                        product=product,
                        user=user,
                        text=f"Ответ на комментарий {comment.id}",
                        type=ProductReviewComment.NodeType.REPLY,
                        parent=comment,
                    )
