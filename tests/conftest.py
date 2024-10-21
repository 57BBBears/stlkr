import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy_utils import create_database, database_exists, drop_database

from src import create_app, db

TESTING_CONFIG = "config.TestingConfig"


@pytest.fixture(scope="session")
def app():
    os.environ["CONFIG"] = TESTING_CONFIG
    print("Using config " + TESTING_CONFIG)

    app = create_app()

    if not app.config["TESTING"]:
        raise ValueError("Not a testing config")

    # app.test_client_class = FlaskLoginClient

    engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    if not database_exists(engine.url):
        create_database(engine.url)

    yield app

    drop_database(engine.url)


@pytest.fixture()
def session(app):
    with app.app_context():
        db.create_all()

        yield db.session

        db.session.close()
        db.drop_all()
