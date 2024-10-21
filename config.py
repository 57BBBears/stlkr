import json
import logging
import os
from os import getenv

from dotenv import load_dotenv

base_dir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(base_dir, ".env"))


def get_log_config(file):
    """Get logging config dictionary from json file."""
    if file and os.path.exists(file):
        with open(file, "r") as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                logging.getLogger().warning(
                    f'Can not decode logging config file "{file}"! ', exc_info=True
                )
            else:
                return config

    return None


class Config:
    TESTING = False
    SECRET_KEY = getenv("SECRET_KEY")
    # db
    SQLALCHEMY_DATABASE_URI = getenv(
        "SQLALCHEMY_DATABASE_URI"
    ) or "sqlite:///" + os.path.join(base_dir, "instance/app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # mail
    MAIL_SERVER = getenv("MAIL_SERVER")
    MAIL_PORT = int(getenv("MAIL_PORT") or 8025)
    MAIL_USE_TLS = getenv("MAIL_USE_TLS") is not None
    MAIL_USERNAME = getenv("MAIL_USERNAME")
    MAIL_PASSWORD = getenv("MAIL_PASSWORD")
    MAIL_FROM = getenv("MAIL_FROM")
    ADMINS = ["admin@test.com"]
    # pagination
    URLS_PER_PAGE = int(getenv("URLS_PER_PAGE") or 10)
    ITEMS_PER_PAGE = int(getenv("ITEMS_PER_PAGE") or 10)
    # parsing
    REDIS_URL = getenv("REDIS_URL")
    QUEUES = getenv("QUEUES").split() if getenv("QUEUES") else ["default"]
    TASK_EXECUTION_TIME = int(getenv("TASK_EXECUTION_TIME") or 600)
    URLS_PER_EXTRACT = int(getenv("URLS_PER_EXTRACT") or 10)
    # other
    LOG_CONFIG = get_log_config(getenv("LOG_CONFIG"))
    # api


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = getenv("TEST_DATABASE_URI") or "sqlite:///:memory:"
    QUEUES = "test"
