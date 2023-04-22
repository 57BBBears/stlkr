import os
import json
import logging
from dotenv import load_dotenv


base_dir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(base_dir, 'instance/.env'))


def get_log_config(file):
    """ Get logging config dictionary from json file. """
    if file and os.path.exists(file):
        with open(file, 'r') as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                logging.getLogger().warning(f'Can not decode logging config file "{file}"! ', exc_info=True)
            else:
                return config

    return None


class Config:
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY')
    # db
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or \
        'sqlite:///' + os.path.join(base_dir, 'instance/app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 8025)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_FROM = os.environ.get('MAIL_FROM')
    ADMINS = ['admin@test.com']
    # pagination
    URLS_PER_PAGE = int(os.environ.get('URLS_PER_PAGE') or 10)
    ITEMS_PER_PAGE = int(os.environ.get('ITEMS_PER_PAGE') or 10)
    # parsing
    REDIS_URL = os.environ.get('REDIS_URL')
    QUEUES = os.environ.get('QUEUES').split() or ['default']
    TASK_EXECUTION_TIME = int(os.environ.get('TASK_EXECUTION_TIME') or 600)
    URLS_PER_EXTRACT = int(os.environ.get('URLS_PER_EXTRACT') or 10)
    # other
    LOG_CONFIG = get_log_config(os.environ.get('LOG_CONFIG'))
    # api


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    QUEUES = 'test'
