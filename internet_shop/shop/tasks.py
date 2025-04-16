from celery import shared_task
from django.core.mail import EmailMessage


@shared_task
def send_email(to_email, subject, message):
    email = EmailMessage(subject, message, "pass", [to_email])
    email.send(fail_silently=False)
