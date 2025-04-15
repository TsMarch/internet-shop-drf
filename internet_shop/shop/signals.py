from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Product
from .tasks import long_task


@receiver(post_save, sender=Product)
def send_email_on_register(sender, instance, created, **kwargs):
    print("got signal")
    long_task.delay()
