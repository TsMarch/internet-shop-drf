from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Order, Product


@receiver(post_save, sender=Product)
def send_email_on_register(sender, instance, created, **kwargs):
    if created:
        pass


@receiver(post_save, sender=Order)
def send_email_after_order(sender, instance, created, **kwargs):
    if created:
        pass
