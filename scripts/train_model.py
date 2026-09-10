"""Train the MediMind symptom classifier.

Usage:
    python scripts/train_model.py [--data data/dataset.csv] [--out models/machine_learning_model.pkl]

The dataset stores each case as a disease label plus up to 17 symptom columns.
We collapse those columns into a single free-text string before vectorising,
because that is the shape real user input arrives in: people type sentences,
not one-hot symptom vectors. Training on text keeps training and inference in
the same representation.
"""

import argparse
import json
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

DEFAULT_DATA = BASE_DIR / 'data' / 'dataset.csv'
DEFAULT_OUT = BASE_DIR / 'models' / 'machine_learning_model.pkl'
DEFAULT_REPORT = BASE_DIR / 'reports' / 'training_metrics.json'

RANDOM_STATE = 42


def clean_symptom(value):
    """'  skin_rash ' -> 'skin rash'."""
    if pd.isna(value):
        return ''
    return str(value).strip().replace('_', ' ').lower()


def load_dataset(path):
    """Return (texts, labels) from a disease/symptom CSV."""
    if not path.exists():
        raise SystemExit(
            f'Dataset not found at {path}.\n'
            'Download dataset.csv from '
            'https://www.kaggle.com/datasets/itachi9604/disease-symptom-description-dataset '
            'and place it there. See data/README.md.'
        )

    frame = pd.read_csv(path)

    label_column = next(
        (c for c in frame.columns if c.strip().lower() == 'disease'), None
    )
    if label_column is None:
        raise SystemExit(f'No "Disease" column found in {path}.')

    symptom_columns = [c for c in frame.columns if c != label_column]

    texts = (
        frame[symptom_columns]
        .apply(lambda row: ', '.join(s for s in map(clean_symptom, row) if s), axis=1)
        .tolist()
    )
    labels = frame[label_column].astype(str).str.strip().tolist()

    keep = [i for i, text in enumerate(texts) if text]
    return [texts[i] for i in keep], [labels[i] for i in keep]


def build_pipeline():
    """TF-IDF over symptom phrases into a calibrated linear classifier.

    LogisticRegression is chosen over a tree ensemble for two reasons: it
    exposes well-behaved predict_proba, which the confidence floor in
    doctor_ai.py depends on, and its coefficients stay inspectable, which
    matters for a medical tool that has to justify itself.
    """
    return Pipeline(
        [
            (
                'tfidf',
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    sublinear_tf=True,
                    min_df=1,
                ),
            ),
            (
                'clf',
                LogisticRegression(
                    max_iter=1000,
                    C=4.0,
                    class_weight='balanced',
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )


def train(data_path=DEFAULT_DATA, out_path=DEFAULT_OUT, report_path=DEFAULT_REPORT):
    texts, labels = load_dataset(data_path)
    print(f'Loaded {len(texts)} cases across {len(set(labels))} conditions.')

    x_train, x_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.2, stratify=labels, random_state=RANDOM_STATE
    )

    pipeline = build_pipeline()

    print('Running 5-fold cross-validation...')
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    cv_scores = cross_val_score(pipeline, x_train, y_train, cv=folds, scoring='accuracy')
    print(f'  CV accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})')

    print('Fitting final model on the training split...')
    pipeline.fit(x_train, y_train)

    train_accuracy = pipeline.score(x_train, y_train)
    test_accuracy = pipeline.score(x_test, y_test)
    print(f'  Train accuracy: {train_accuracy:.4f}')
    print(f'  Test accuracy:  {test_accuracy:.4f}')

    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, out_path)
    print(f'Model written to {out_path}')

    metrics = {
        'n_samples': len(texts),
        'n_classes': len(set(labels)),
        'cv_accuracy_mean': round(float(cv_scores.mean()), 4),
        'cv_accuracy_std': round(float(cv_scores.std()), 4),
        'train_accuracy': round(float(train_accuracy), 4),
        'test_accuracy': round(float(test_accuracy), 4),
        'model': 'TfidfVectorizer(1,2) + LogisticRegression',
        'random_state': RANDOM_STATE,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(metrics, indent=2), encoding='utf-8')
    print(f'Metrics written to {report_path}')

    return pipeline, metrics


def main():
    parser = argparse.ArgumentParser(description='Train the MediMind classifier.')
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    parser.add_argument('--report', type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    train(args.data, args.out, args.report)


if __name__ == '__main__':
    main()
