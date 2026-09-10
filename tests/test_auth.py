"""Auth: the v1 scaffold accepted any credentials and looped forever."""

from app.auth.models import User
from database import db


def test_signup_creates_user_and_signs_them_in(client, app):
    response = client.post(
        '/signup',
        data={
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'StrongPass123',
            'confirm_password': 'StrongPass123',
            'gender': '',
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.username == 'newuser'))
        assert user is not None
        assert user.password_hash != 'StrongPass123'
        assert user.check_password('StrongPass123')


def test_signup_rejects_duplicate_username(client, make_user):
    make_user(username='taken')
    response = client.post(
        '/signup',
        data={
            'username': 'taken',
            'email': 'other@example.com',
            'password': 'StrongPass123',
            'confirm_password': 'StrongPass123',
            'gender': '',
        },
    )
    assert b'already taken' in response.data


def test_signup_rejects_mismatched_passwords(client):
    response = client.post(
        '/signup',
        data={
            'username': 'mismatch',
            'email': 'mismatch@example.com',
            'password': 'StrongPass123',
            'confirm_password': 'DifferentPass123',
            'gender': '',
        },
    )
    assert b'must match' in response.data


def test_login_with_correct_password_reaches_dashboard(client, make_user, login):
    make_user()
    response = login()
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/dashboard')


def test_login_with_wrong_password_is_rejected(client, make_user, login):
    make_user()
    response = login(password='WrongPassword')
    assert b'Incorrect username or password' in response.data


def test_login_with_unknown_user_is_rejected(client, login):
    response = login(username='ghost')
    assert b'Incorrect username or password' in response.data


def test_dashboard_requires_login(client):
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_no_redirect_loop_after_login(client, make_user, login):
    """v1 bug: login redirected to a dashboard that redirected back to login."""
    make_user()
    login()
    response = client.get('/dashboard')
    assert response.status_code == 200


def test_logout_ends_the_session(client, make_user, login):
    make_user()
    login()
    client.get('/logout')
    assert client.get('/dashboard').status_code == 302


def test_login_ignores_offsite_next_target(client, make_user):
    make_user()
    response = client.post(
        '/login?next=http://evil.example.com/steal',
        data={'username': 'farwa', 'password': 'StrongPass123'},
    )
    assert 'evil.example.com' not in response.headers['Location']
