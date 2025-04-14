from celery import shared_task
from django.core.mail import send_mail


@shared_task
def send_welcome_email(user_email):
    send_mail(
        subject="Добро пожаловать!", message="Спасибо за регистрацию!", from_email=None, recipient_list=[user_email]
    )
