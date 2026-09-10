"""Training pipeline tests.

These run without the Kaggle dataset: a small synthetic CSV in the same shape
exercises loading, training, persistence and the contract that doctor_ai.py
depends on (a fitted pipeline that takes raw text and exposes predict_proba).
"""

import joblib
import pandas as pd
import pytest

from doctor_ai import DoctorAI
from scripts.train_model import build_pipeline, clean_symptom, load_dataset, train

CASES = [
    ('Common cold', ['runny_nose', 'sneezing', 'sore_throat', 'mild_cough']),
    ('Influenza', ['high_fever', 'body_ache', 'chills', 'fatigue']),
    ('Migraine', ['headache', 'nausea', 'light_sensitivity', 'throbbing_pain']),
    ('Gastroenteritis', ['diarrhea', 'vomiting', 'stomach_pain', 'cramps']),
]


@pytest.fixture
def dataset_csv(tmp_path):
    """A CSV shaped like the Kaggle dataset: Disease + Symptom_1..n."""
    rows = []
    for disease, symptoms in CASES:
        for _ in range(12):
            row = {'Disease': disease}
            for index, symptom in enumerate(symptoms, start=1):
                row[f'Symptom_{index}'] = symptom
            rows.append(row)

    path = tmp_path / 'dataset.csv'
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_clean_symptom_normalises_formatting():
    assert clean_symptom('  Skin_Rash ') == 'skin rash'
    assert clean_symptom(None) == ''


def test_load_dataset_collapses_symptoms_into_text(dataset_csv):
    texts, labels = load_dataset(dataset_csv)
    assert len(texts) == len(labels) == 48
    assert 'runny nose' in texts[0]
    assert '_' not in texts[0]
    assert set(labels) == {case[0] for case in CASES}


def test_load_dataset_reports_a_missing_file(tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        load_dataset(tmp_path / 'nope.csv')
    assert 'kaggle' in str(excinfo.value).lower()


def test_pipeline_learns_the_training_signal(dataset_csv):
    texts, labels = load_dataset(dataset_csv)
    pipeline = build_pipeline()
    pipeline.fit(texts, labels)
    assert pipeline.predict(['runny nose, sneezing, sore throat'])[0] == 'Common cold'


def test_train_writes_a_model_and_metrics(dataset_csv, tmp_path):
    out = tmp_path / 'model.pkl'
    report = tmp_path / 'metrics.json'
    pipeline, metrics = train(dataset_csv, out, report)

    assert out.exists() and out.stat().st_size > 0
    assert report.exists()
    assert metrics['n_classes'] == len(CASES)
    assert 0 <= metrics['test_accuracy'] <= 1


def test_saved_model_satisfies_the_doctor_ai_contract(dataset_csv, tmp_path):
    """doctor_ai calls predict_proba on raw text and reads classes_."""
    out = tmp_path / 'model.pkl'
    train(dataset_csv, out, tmp_path / 'metrics.json')

    doctor = DoctorAI(model_path=out, min_confidence=0.1)
    assert doctor.model is not None

    condition, confidence = doctor.predict_condition('runny nose, sneezing, sore throat')
    assert condition == 'Common cold'
    assert 0 < confidence <= 1


def test_red_flags_still_win_over_a_trained_model(dataset_csv, tmp_path):
    """A trained model must never be able to downgrade an emergency."""
    out = tmp_path / 'model.pkl'
    train(dataset_csv, out, tmp_path / 'metrics.json')

    doctor = DoctorAI(model_path=out, min_confidence=0.1)
    result = doctor.analyze_symptoms('runny nose, sneezing and severe chest pain')

    assert result['triage_level'] == 'emergency'
    assert result['condition'] is None


def test_corrupt_model_falls_back_to_the_baseline(tmp_path):
    path = tmp_path / 'broken.pkl'
    path.write_bytes(b'not a pickle')

    doctor = DoctorAI(model_path=path)
    assert doctor.model is None
    result = doctor.analyze_symptoms('runny nose, sneezing, sore throat, cough, congestion')
    assert result['condition'] == 'Common cold'
