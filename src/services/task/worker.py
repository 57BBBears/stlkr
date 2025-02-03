from celery import Celery

celery = Celery(config_source="src.services.task.celeryconfig")
