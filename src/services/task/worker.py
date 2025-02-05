from celery import Celery
from sqlalchemy import NullPool, create_engine
from sqlalchemy.orm import Session

from config import Config

celery = Celery(config_source="src.services.task.celeryconfig")
session = Session(create_engine(Config.SQLALCHEMY_DATABASE_URI, poolclass=NullPool))
