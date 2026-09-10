import pytest

from app import create_app
from app.auth.models import User
from database import db


@pytest.fixture
def app():
    application = create_app('testing')
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user(app):
    def _make(username='farwa', password='StrongPass123', email=None):
        with app.app_context():
            user = User(username=username, email=email or f'{username}@example.com')
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return user.id

    return _make


@pytest.fixture
def login(client):
    def _login(username='farwa', password='StrongPass123'):
        return client.post(
            '/login',
            data={'username': username, 'password': password},
            follow_redirects=False,
        )

    return _login
