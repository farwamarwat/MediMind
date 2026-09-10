# doctor_ai.py
"""Symptom triage engine.

MediMind is a *triage and guidance* tool, not a diagnostic one. Two layers run
on every request:

1. A deterministic red-flag check for symptoms that always warrant emergency
   care. This never depends on the ML model and cannot be overridden by it.
2. A trained classifier that suggests a likely condition with a confidence
   score. Below `min_confidence` the suggestion is withheld entirely rather
   than shown as a guess.
"""

import logging
import re

import joblib

from triage import TriageLevel

logger = logging.getLogger(__name__)

DISCLAIMER = (
    'MediMind provides general health information only. It is not a doctor '
    'and does not diagnose or prescribe. Always consult a qualified '
    'healthcare professional about your symptoms.'
)

# Symptoms that send a user straight to emergency care, whatever else is said.
RED_FLAGS = {
    r'\bchest (pain|pressure|tightness)\b': 'chest pain',
    r'\b(cant|cannot|can not|difficulty|trouble) breath': 'difficulty breathing',
    r'\bshortness of breath\b': 'shortness of breath',
    r'\bcough(ing)? (up )?blood\b': 'coughing blood',
    r'\bvomit(ing)? blood\b': 'vomiting blood',
    r'\b(severe|heavy|uncontrolled) bleeding\b': 'severe bleeding',
    r'\b(unconscious|fainted|passed out|unresponsive)\b': 'loss of consciousness',
    r'\b(seizure|convulsion|fitting)\b': 'seizure',
    r'\b(slurred speech|face droop|facial droop)\b': 'possible stroke',
    r'\bnumbness (on )?one side\b': 'possible stroke',
    r'\bstiff neck\b.*\bfever\b|\bfever\b.*\bstiff neck\b': 'fever with stiff neck',
    r'\b(blue|bluish) (lips|skin)\b': 'cyanosis',
    r'\b(suicidal|kill myself|end my life|self harm)\b': 'mental health crisis',
    r'\bsevere abdominal pain\b': 'severe abdominal pain',
}

# Fallback keyword matcher, used only when no trained model is available so the
# app still runs end to end on a fresh clone. Replaced by the real classifier.
BASELINE_RULES = [
    ('Common cold', {'runny nose', 'sneezing', 'sore throat', 'cough', 'congestion'}),
    ('Influenza', {'fever', 'body ache', 'chills', 'fatigue', 'headache', 'cough'}),
    ('Migraine', {'headache', 'nausea', 'light sensitivity', 'aura', 'throbbing'}),
    ('Gastroenteritis', {'diarrhea', 'vomiting', 'stomach pain', 'nausea', 'cramps'}),
    ('Allergic rhinitis', {'itchy eyes', 'sneezing', 'runny nose', 'rash', 'itching'}),
    ('Dehydration', {'thirst', 'dizziness', 'dry mouth', 'dark urine', 'fatigue'}),
]

URGENT_KEYWORDS = {
    'high fever', 'persistent vomiting', 'dehydration', 'severe pain',
    'blood in stool', 'blood in urine', 'rapid heartbeat',
}


class DoctorAI:
    def __init__(self, model_path=None, min_confidence=0.25):
        self.model_path = model_path
        self.min_confidence = min_confidence
        self.model = None
        if model_path:
            self.load_model(model_path)

    def load_model(self, model_path=None):
        """Load the trained pipeline. Falls back to rules if unavailable."""
        path = model_path or self.model_path
        try:
            if path and path.exists() and path.stat().st_size > 0:
                self.model = joblib.load(path)
                logger.info('Loaded triage model from %s', path)
            else:
                logger.warning(
                    'No trained model at %s - using rule-based baseline.', path
                )
        except Exception:
            logger.exception('Failed to load model at %s; using baseline.', path)
            self.model = None
        return self.model

    def analyze_symptoms(self, symptoms):
        """Return a triage result for a free-text symptom description."""
        text = (symptoms or '').strip()
        if not text:
            raise ValueError('Please describe your symptoms.')

        normalised = text.lower()

        red_flags = self.detect_red_flags(normalised)
        if red_flags:
            return {
                'condition': None,
                'confidence': None,
                'triage_level': TriageLevel.EMERGENCY,
                'red_flags': red_flags,
                'advice': (
                    'Your description mentions '
                    f"{', '.join(red_flags)}, which needs immediate medical "
                    'attention. Go to the nearest emergency department or call '
                    'emergency services (Rescue 1122) now. Do not wait.'
                ),
                'disclaimer': DISCLAIMER,
            }

        condition, confidence = self.predict_condition(normalised)

        if condition is None or confidence < self.min_confidence:
            return {
                'condition': None,
                'confidence': confidence,
                'triage_level': TriageLevel.SEE_DOCTOR,
                'red_flags': [],
                'advice': (
                    'MediMind could not match your symptoms to a condition with '
                    'enough confidence to say anything useful. Please describe '
                    'them in more detail, or see a doctor for a proper '
                    'assessment.'
                ),
                'disclaimer': DISCLAIMER,
            }

        triage = self.assess_urgency(normalised, confidence)
        return {
            'condition': condition,
            'confidence': confidence,
            'triage_level': triage,
            'red_flags': [],
            'advice': self.suggest_care(condition, triage),
            'disclaimer': DISCLAIMER,
        }

    def detect_red_flags(self, normalised_text):
        """Return the emergency indicators present in the text."""
        found = []
        for pattern, label in RED_FLAGS.items():
            if re.search(pattern, normalised_text):
                found.append(label)
        return found

    def predict_condition(self, normalised_text):
        """Return (condition, confidence). Uses the model when loaded."""
        if self.model is not None:
            try:
                probabilities = self.model.predict_proba([normalised_text])[0]
                best = probabilities.argmax()
                return str(self.model.classes_[best]), float(probabilities[best])
            except Exception:
                logger.exception('Model inference failed; falling back to rules.')

        return self._baseline_predict(normalised_text)

    def _baseline_predict(self, normalised_text):
        best_condition, best_score = None, 0.0
        for condition, keywords in BASELINE_RULES:
            hits = sum(1 for keyword in keywords if keyword in normalised_text)
            if hits:
                score = hits / len(keywords)
                if score > best_score:
                    best_condition, best_score = condition, score
        return best_condition, best_score

    def assess_urgency(self, normalised_text, confidence):
        if any(keyword in normalised_text for keyword in URGENT_KEYWORDS):
            return TriageLevel.URGENT
        if confidence < 0.5:
            return TriageLevel.SEE_DOCTOR
        return TriageLevel.SELF_CARE

    def suggest_care(self, condition, triage_level):
        """General care guidance. Deliberately never names a specific drug."""
        base = {
            TriageLevel.SELF_CARE: (
                f'Your symptoms are consistent with {condition}, which can '
                'usually be managed at home with rest and fluids. If they '
                'worsen or last more than a few days, see a doctor.'
            ),
            TriageLevel.SEE_DOCTOR: (
                f'Your symptoms may point to {condition}, but this needs a '
                'proper examination. Book an appointment with a doctor in the '
                'next few days.'
            ),
            TriageLevel.URGENT: (
                f'Your symptoms may point to {condition} and include signs '
                'that should not wait. See a doctor within 24 hours.'
            ),
        }.get(triage_level, 'Please consult a doctor about your symptoms.')

        return (
            f'{base} Any medicine - including over-the-counter medicine - '
            'should be chosen with a pharmacist or doctor, not from this app.'
        )
