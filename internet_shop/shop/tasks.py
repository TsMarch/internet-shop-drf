from celery import shared_task


@shared_task
def long_task():
    print(">>> Starting long task...")
    print(">>> Long task completed.")
    return "Finished"
