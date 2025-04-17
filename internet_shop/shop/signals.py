from django.db.models.signals import post_save
from django.dispatch import Signal, receiver

from .models import User
from .tasks import send_email

order_fully_created = Signal()


@receiver(post_save, sender=User)
def send_email_on_register(sender, instance, created, **kwargs):
    if created:
        subject = f"Привет, {instance.username}"
        message = "Привет и добро пожаловать!"
        recipient = instance.email
        send_email.delay(subject=subject, message=message, recipient=recipient)


@receiver(order_fully_created)
def send_email_after_order(sender, order_items, user, total_sum, **kwargs):
    subject = f"Спасибо за заказ, {user.username}!"
    recipient = user.email
    lines = []
    for item in order_items:
        lines.append(f"{item.product.name} — {item.quantity} шт. по {item.price} ₽")
    message = "Ваш заказ:\n" + "\n".join(lines) + f"\nИтого: {total_sum} ₽"
    send_email.delay(subject=subject, message=message, recipient=recipient)
