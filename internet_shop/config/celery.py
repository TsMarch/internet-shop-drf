from django.conf import settings

from celery import Celery

settings.configure()

app = Celery("shop")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
