# Generated by Django 5.0.7 on 2024-08-05 12:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0005_remove_product_old_price"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="old_price",
            field=models.DecimalField(
                decimal_places=2,
                default=1000,
                max_digits=10,
                verbose_name="Цена без скидки",
            ),
            preserve_default=False,
        ),
    ]
