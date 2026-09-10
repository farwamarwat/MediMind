"""Consultation flow: persistence, ownership and the emergency path."""

from app.models import Consultation
from database import db
from triage import TriageLevel


def test_consultation_requires_login(client):
    assert client.get('/consultation').status_code == 302


def test_consultation_is_saved_and_redirects(client, app, make_user, login):
    make_user()
    login()
    response = client.post(
        '/consultation',
        data={'symptoms': 'runny nose, sneezing, sore throat, cough, congestion'},
    )
    assert response.status_code == 302
    with app.app_context():
        records = db.session.scalars(db.select(Consultation)).all()
        assert len(records) == 1
        assert records[0].predicted_condition == 'Common cold'


def test_short_symptoms_are_rejected(client, app, make_user, login):
    make_user()
    login()
    response = client.post('/consultation', data={'symptoms': 'ill'})
    assert b'more detail' in response.data
    with app.app_context():
        assert db.session.scalars(db.select(Consultation)).all() == []


def test_emergency_result_is_shown_to_the_user(client, make_user, login):
    make_user()
    login()
    response = client.post(
        '/consultation',
        data={'symptoms': 'severe chest pain spreading to my left arm'},
        follow_redirects=True,
    )
    assert b'Rescue 1122' in response.data
    assert b'Emergency' in response.data


def test_emergency_is_stored_with_the_right_level(client, app, make_user, login):
    make_user()
    login()
    client.post(
        '/consultation', data={'symptoms': 'I am coughing blood since this morning'}
    )
    with app.app_context():
        record = db.session.scalar(db.select(Consultation))
        assert record.triage_level == TriageLevel.EMERGENCY


def test_user_cannot_read_another_users_consultation(client, app, make_user, login):
    owner_id = make_user(username='owner')
    make_user(username='farwa')

    with app.app_context():
        record = Consultation(
            user_id=owner_id,
            symptoms_text='private symptoms',
            triage_level=TriageLevel.SELF_CARE,
            advice='rest',
        )
        db.session.add(record)
        db.session.commit()
        record_id = record.id

    login()
    response = client.get(f'/consultation/{record_id}')
    assert response.status_code == 404
    assert b'private symptoms' not in response.data


def test_missing_consultation_returns_404(client, make_user, login):
    make_user()
    login()
    assert client.get('/consultation/9999').status_code == 404


def test_history_lists_past_checks(client, make_user, login):
    make_user()
    login()
    client.post(
        '/consultation',
        data={'symptoms': 'runny nose, sneezing, sore throat, cough, congestion'},
    )
    response = client.get('/history')
    assert response.status_code == 200
    assert b'Common cold' in response.data or b'Manageable at home' in response.data
