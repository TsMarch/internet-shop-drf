import random

from django.core.management.base import BaseCommand
from django.db import transaction
from shop.models import Product, ReviewComment, User


class Command(BaseCommand):
    help = "Generate test data for reviews"

    def handle(self, *args, **kwargs):
        users = User.objects.all()

        batch_size = 10000
        total_reviews = 100000
        reviews_left = total_reviews

        products_per_page = 1000
        product_offset = 0

        with transaction.atomic():
            while reviews_left > 0:
                products = Product.objects.all()[product_offset : product_offset + products_per_page]
                product_offset += products_per_page
                if not products:
                    break

                while reviews_left > 0 and products:
                    reviews_to_create = min(reviews_left, batch_size)
                    reviews_left -= reviews_to_create

                    for _ in range(reviews_to_create):
                        product = random.choice(products)
                        user = random.choice(users)
                        rating = random.choice([1, 2, 3, 4, 5])
                        text = f"Отзыв пользователя {user.username} для товара {product.name}. Рейтинг: {rating}."
                        parent = None

                        review = ReviewComment(
                            product=product,
                            user=user,
                            rating=rating,
                            text=text,
                            parent=parent,
                        )
                        review.save()

                    print(f"Осталось отзывов: {reviews_left}")
