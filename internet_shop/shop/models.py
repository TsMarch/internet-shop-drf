import eav
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models

# from django.db.models import Q


class ProductCategory(models.Model):
    name = models.CharField("Название категории", max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Категории товаров"

    def __str__(self):
        return f"{self.name}"


class Product(models.Model):
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT)
    id = models.AutoField(primary_key=True)
    name = models.CharField("Имя", max_length=100, blank=False)
    description = models.CharField("Описание", max_length=300, blank=True)
    old_price = models.DecimalField("Цена без скидки", decimal_places=2, max_digits=10)
    discount = models.PositiveIntegerField("Процент скидки")
    price = models.DecimalField(
        "Цена со скидкой",
        decimal_places=2,
        max_digits=10,
        null=True,
        blank=True,
        editable=False,
    )
    available = models.BooleanField("Доступность товара", default=True)
    available_quantity = models.PositiveIntegerField("Остаток товара на складе", default=0)

    class Meta:
        verbose_name_plural = "Товары"

    def __str__(self):
        return f"Название товара: {self.name}; Цена со скидкой: {self.price}; Скидка: {self.discount}%"

    def clean(self, *args, **kwargs):
        if not self.available and self.available_quantity > 0:
            raise ValidationError("Невозможно наличие товара на складе если он недоступен")
        super().save()


eav.register(Product)


class ProductReviewComment(models.Model):
    class RatingChoices(models.IntegerChoices):
        ONE = 1
        TWO = 2
        THREE = 3
        FOUR = 4
        FIVE = 5

    class NodeType(models.TextChoices):
        REVIEW = "review"
        COMMENT = "comment"
        REPLY = "reply"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews", null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField("Текст", blank=True, null=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")
    type = models.CharField(max_length=10, choices=NodeType.choices, default=NodeType.REVIEW)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    rating = models.IntegerField(choices=RatingChoices.choices, verbose_name="Rating", null=True)

    class Meta:
        ordering = ["created_at"]

    #       constraints = [
    #         models.UniqueConstraint(
    #            fields=["product", "user"],
    #           condition=Q(type="review"),
    #          name="unique_review_per_product_per_user",
    #     )
    # ]

    def clean(self):
        if self.type != ProductReviewComment.NodeType.REVIEW and self.rating is not None:
            raise ValidationError("Только отзыв может содержать рейтинг")
        super().clean()


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Корзина"

    def __str__(self):
        return f"Корзина {self.user}"


class CartItems(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(
        "Цена со скидкой",
        decimal_places=2,
        max_digits=10,
        null=True,
        blank=True,
        editable=False,
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    active_flag = models.BooleanField(blank=True, default=True)
    delivery_flag = models.BooleanField(blank=True, default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    total_sum = models.DecimalField("Сумма заказа", decimal_places=6, max_digits=20, null=True)
    products = models.ManyToManyField(Product, through="OrderItems", related_name="orders")


class OrderItems(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(
        "Цена со скидкой",
        decimal_places=2,
        max_digits=10,
        null=True,
        blank=True,
        editable=False,
    )
    quantity = models.PositiveIntegerField(default=1)


class UserBalance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    balance = models.DecimalField("Баланс юзера", decimal_places=6, max_digits=20, null=False, default=0)


class UserBalanceHistory(models.Model):
    class OperationType(models.TextChoices):
        DEPOSIT = "deposit"
        PAYMENT = "payment"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    operation_type = models.CharField("Тип операции", max_length=7, blank=False, choices=OperationType)
    amount = models.DecimalField("Сумма операции", decimal_places=6, max_digits=20, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
