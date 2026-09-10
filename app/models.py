# app/models.py

from datetime import datetime, timezone

from database import db
from triage import TriageLevel


class Consultation(db.Model):
    __tablename__ = 'consultations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('users.id'), nullable=False, index=True
    )

    symptoms_text = db.Column(db.Text, nullable=False)
    predicted_condition = db.Column(db.String(120))
    confidence = db.Column(db.Float)
    triage_level = db.Column(db.String(20), nullable=False)
    advice = db.Column(db.Text)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    user = db.relationship('User', back_populates='consultations')

    @property
    def triage_label(self):
        return TriageLevel.LABELS.get(self.triage_level, 'Unknown')

    @property
    def confidence_percent(self):
        return round((self.confidence or 0) * 100)

    def __repr__(self):
        return f'<Consultation {self.id} user={self.user_id}>'
