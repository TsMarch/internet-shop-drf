from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Order, User
from .tasks import send_email


@receiver(post_save, sender=User)
def send_email_on_register(sender, instance, created, **kwargs):
    if created:
        subject = f"Привет, {instance.username}"
        message = "Привет и добро пожаловать!"
        recipient = instance.email
        send_email.delay(subject=subject, message=message, recipient=recipient)


@receiver(post_save, sender=Order)
def send_email_after_order(sender, instance, created, **kwargs):
    if created:
        pass
