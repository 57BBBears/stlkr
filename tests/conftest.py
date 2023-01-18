import pytest
from app import create_app, db
from config import TestingConfig

TESTING_CONFIG = TestingConfig


@pytest.fixture(scope='class', params=[TESTING_CONFIG])
def _get_app(request):
    print('Using config ' + request.param.__name__)
    return create_app(request.param)


@pytest.fixture(scope='class')
def setup_app(request, _get_app):
    request.cls.app = _get_app


@pytest.fixture(scope='class')
def setup_db(request, _get_app):
    app = _get_app
    app.app_context().push()
    request.cls.db = db
    db.create_all()
    yield
    db.session.remove()

