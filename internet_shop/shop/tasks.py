from celery import shared_task
from django.core.mail import send_mail


@shared_task
def send_email(subject, message, recipient):
    send_mail(subject=subject, message=message, from_email=None, recipient_list=recipient, fail_silently=False)
