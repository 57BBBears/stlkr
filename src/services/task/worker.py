from celery import Celery

app = Celery(config_source="src.services.task.celeryconfig")
