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
    RECAPTCHA_PUBLIC_KEY = getenv("RECAPTCHA_PUBLIC_KEY")
    RECAPTCHA_PRIVATE_KEY = getenv("RECAPTCHA_PRIVATE_KEY")
    FLASK_ADMIN_SWATCH = getenv("FLASK_ADMIN_SWATCH", "cerulean")
    # core
    CORE_DOMAIN = getenv("CORE_DOMAIN", "localhost:5000")
    PUBLIC_TEMPLATE_FOLDER = os.path.abspath(
        getenv("PUBLIC_TEMPLATE_FOLDER", "instance/templates")
    )
    # db
    SQLALCHEMY_DATABASE_URI = getenv("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # mail
    MAIL_SERVER = getenv("MAIL_SERVER")
    MAIL_PORT = int(getenv("MAIL_PORT") or 8025)
    MAIL_USE_TLS = getenv("MAIL_USE_TLS") is not None
    MAIL_USERNAME = getenv("MAIL_USERNAME")
    MAIL_PASSWORD = getenv("MAIL_PASSWORD")
    MAIL_FROM = getenv("MAIL_FROM")
    ADMINS = ("admin@test.com",)
    # pagination
    URLS_PER_PAGE = int(getenv("URLS_PER_PAGE") or 10)
    ITEMS_PER_PAGE = int(getenv("ITEMS_PER_PAGE") or 10)
    # parsing
    TASK_BROKER_URI = getenv("TASK_BROKER_URI")
    TASK_SOFT_TIME_LIMIT = int(getenv("TASK_SOFT_TIME_LIMIT") or 5 * 60)
    TASK_TIME_LIMIT = int(getenv("TASK_TIME_LIMIT") or 5 * 60 + 60)
    # import
    MAX_IMPORT_FILE_SIZE_KB = int(getenv("MAX_IMPORT_FILE_SIZE_KB") or 100)
    # other
    LOG_CONFIG = get_log_config(getenv("LOG_CONFIG"))


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = getenv("TEST_DATABASE_URI")
    QUEUES = "test"
