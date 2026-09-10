"""The triage engine must never let the model override an emergency signal."""

import pytest

from doctor_ai import DoctorAI
from triage import TriageLevel


@pytest.fixture
def doctor():
    return DoctorAI(min_confidence=0.25)


@pytest.mark.parametrize(
    'text',
    [
        'I have severe chest pain and it spreads to my arm',
        'my father is unconscious and not responding',
        'I am coughing blood since morning',
        'having trouble breathing since last night',
        'she had a seizure ten minutes ago',
    ],
)
def test_red_flags_escalate_to_emergency(doctor, text):
    result = doctor.analyze_symptoms(text)
    assert result['triage_level'] == TriageLevel.EMERGENCY
    assert result['red_flags']
    assert 'emergency' in result['advice'].lower()


def test_emergency_never_names_a_condition(doctor):
    result = doctor.analyze_symptoms('crushing chest pain and sweating')
    assert result['condition'] is None


def test_low_confidence_is_withheld(doctor):
    result = doctor.analyze_symptoms('I feel a bit strange today, hard to explain')
    assert result['condition'] is None
    assert result['triage_level'] == TriageLevel.SEE_DOCTOR


def test_recognisable_symptoms_return_a_condition(doctor):
    result = doctor.analyze_symptoms(
        'runny nose, sneezing, sore throat and a cough with congestion'
    )
    assert result['condition'] == 'Common cold'
    assert 0 < result['confidence'] <= 1


def test_urgent_keywords_raise_the_level(doctor):
    result = doctor.analyze_symptoms(
        'diarrhea, vomiting, stomach pain, nausea and cramps with dehydration'
    )
    assert result['triage_level'] == TriageLevel.URGENT


def test_empty_symptoms_rejected(doctor):
    with pytest.raises(ValueError):
        doctor.analyze_symptoms('   ')


def test_advice_never_names_a_medicine(doctor):
    result = doctor.analyze_symptoms('headache, nausea, throbbing and aura')
    banned = ['paracetamol', 'ibuprofen', 'panadol', 'antibiotic', 'mg']
    assert not any(word in result['advice'].lower() for word in banned)


def test_every_result_carries_a_disclaimer(doctor):
    for text in ['chest pain', 'sneezing and runny nose', 'vague feeling']:
        assert doctor.analyze_symptoms(text)['disclaimer']
