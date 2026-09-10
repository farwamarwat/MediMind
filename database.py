# database.py
"""Data-access layer for MediMind.

Owns the SQLAlchemy instance so that models and the app factory can share it
without importing each other.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app):
    """Bind SQLAlchemy to the app and create any missing tables."""
    db.init_app(app)
    with app.app_context():
        # Imported for their side effect: registering the mappers.
        from app.auth.models import User  # noqa: F401
        from app.models import Consultation  # noqa: F401

        db.create_all()


def retrieve_user_data(user_id):
    """Return a user's profile, or None if no such user exists."""
    from app.auth.models import User

    return db.session.get(User, user_id)


def retrieve_consultation_data(user_id, limit=None):
    """Return a user's consultations, most recent first."""
    from app.models import Consultation

    query = (
        db.select(Consultation)
        .where(Consultation.user_id == user_id)
        .order_by(Consultation.created_at.desc())
    )
    if limit is not None:
        query = query.limit(limit)
    return db.session.scalars(query).all()


def store_consultation(consultation):
    """Persist a consultation record."""
    db.session.add(consultation)
    db.session.commit()
    return consultation
