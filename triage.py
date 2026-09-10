# triage.py
"""Triage vocabulary shared by the model layer and the data layer.

Kept at the top level, outside the `app` package, so that `doctor_ai` and
`app.models` can both use it without importing each other.
"""


class TriageLevel:
    """How urgently a user should seek human care.

    MediMind never diagnoses; it routes. Every consultation is assigned one of
    these regardless of how confident the model is about the condition itself.
    """

    SELF_CARE = 'self_care'
    SEE_DOCTOR = 'see_doctor'
    URGENT = 'urgent'
    EMERGENCY = 'emergency'

    LABELS = {
        SELF_CARE: 'Manageable at home',
        SEE_DOCTOR: 'See a doctor within a few days',
        URGENT: 'Seek care within 24 hours',
        EMERGENCY: 'Emergency - go to a hospital now',
    }

    # Colour keys consumed by the templates, ordered least to most urgent.
    ORDER = [SELF_CARE, SEE_DOCTOR, URGENT, EMERGENCY]
