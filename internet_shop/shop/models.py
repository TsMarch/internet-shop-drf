from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ValidationError


class ProductCategory(models.Model):
    name = models.CharField("Название категории", max_length=100)

    class Meta:
        verbose_name_plural = "Категории товаров"

    def __str__(self):
        return f"{self.name}"


class Product(models.Model):
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT)
    name = models.CharField("Имя", max_length=100, blank=False)
    description = models.CharField("Описание", max_length=300, blank=True)
    old_price = models.DecimalField("Цена без скидки", decimal_places=2, max_digits=10)
    discount = models.PositiveIntegerField("Процент скидки")
    price = models.DecimalField("Цена со скидкой", decimal_places=2, max_digits=10)
    available = models.BooleanField("Доступность товара", default=True)
    available_quantity = models.PositiveIntegerField("Остаток товара на складе", default=0)

    class Meta:
        verbose_name_plural = "Товары"

    def __str__(self):
        return f"Название товара: {self.name}; Цена со скидкой: {self.price}; Скидка: {self.discount}%"

    @property
    def price(self):
        return self.old_price - self.old_price * self.discount / 100

    def clean(self):
        if not self.available and self.available_quantity > 0:
            raise ValidationError("Невозможно наличие товара на складе если он недоступен")
        super().save()


class Cart(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Корзина"

    def __str__(self):
        return f"{self.product.name}"
