from golink.app import create_app, create_celery
from golink.extensions import db

import pytest


@pytest.fixture
def app():

    current_app = create_app(run_mode='test')
    create_celery(current_app)

    # Establish an application context before running the tests.
    ctx = current_app.app_context()
    ctx.push()

    return current_app


@pytest.fixture
def client():

    current_app = create_app(run_mode='test')
    create_celery(current_app)

    with current_app.test_client() as client:
        with current_app.app_context():
            db.create_all()

    yield client
