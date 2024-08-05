from django.db import models
from django.core.exceptions import ValidationError


class ProductCategory(models.Model):
    name = models.CharField("Название категории", max_length=100)

    class Meta:
        verbose_name_plural = "Product categories"

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

    def __str__(self):
        return f"Название товара: {self.name}; Цена со скидкой: {self.price}; Скидка: {self.discount}%"

    @property
    def price(self):
        return self.old_price - self.old_price * self.discount/100

    def clean(self):
        if not self.available and self.available_quantity > 0:
            raise ValidationError("Невозможно наличие товара на складе если он недоступен")
        super().save()


