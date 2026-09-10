"""Evaluate the MediMind classifier - including how it fails.

Headline accuracy on this dataset is close to perfect, which says more about
the dataset than about the model. This script therefore reports three things:

1. Standard metrics: per-class precision, recall and F1, plus a confusion
   matrix image.
2. A robustness study: the same test cases rewritten the way a real user would
   type them - reordered, incomplete, wrapped in a sentence, misspelled. The
   gap between clean and perturbed accuracy is the honest measure of how much
   the headline number is worth.
3. A confidence audit: how often the model is confidently wrong, which is the
   failure mode that matters most for a triage tool.

Usage:
    python scripts/evaluate_model.py
"""

import json
import random
import sys
from pathlib import Path

import joblib
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    accuracy_score,
    classification_report,
    confusion_matrix,
)
from sklearn.model_selection import train_test_split  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from scripts.train_model import (  # noqa: E402
    DEFAULT_DATA,
    DEFAULT_OUT,
    RANDOM_STATE,
    load_dataset,
)

REPORTS_DIR = BASE_DIR / 'reports'
PROBES_PATH = BASE_DIR / 'data' / 'layperson_probes.json'

FILLER_TEMPLATES = [
    'I have been having {} for the last two days',
    'doctor, I am suffering from {}',
    'since yesterday there is {} and it is not getting better',
    'my symptoms are {}, please help',
]


def _symptoms_of(text):
    return [part.strip() for part in text.split(',') if part.strip()]


def perturb_reorder(text, rng):
    symptoms = _symptoms_of(text)
    rng.shuffle(symptoms)
    return ', '.join(symptoms)


def perturb_drop(text, rng):
    """Users rarely list every symptom. Drop roughly a third of them."""
    symptoms = _symptoms_of(text)
    if len(symptoms) <= 1:
        return text
    keep = max(1, int(len(symptoms) * 0.67))
    return ', '.join(rng.sample(symptoms, keep))


def perturb_sentence(text, rng):
    symptoms = _symptoms_of(text)
    if len(symptoms) > 1:
        body = ', '.join(symptoms[:-1]) + ' and ' + symptoms[-1]
    else:
        body = text
    return rng.choice(FILLER_TEMPLATES).format(body)


def perturb_typos(text, rng):
    """Swap two adjacent characters in a third of the words."""
    words = []
    for word in text.split(' '):
        if len(word) > 4 and rng.random() < 0.33:
            i = rng.randrange(1, len(word) - 2)
            word = word[:i] + word[i + 1] + word[i] + word[i + 2:]
        words.append(word)
    return ' '.join(words)


PERTURBATIONS = {
    'reordered symptoms': perturb_reorder,
    'incomplete list (33% dropped)': perturb_drop,
    'written as a sentence': perturb_sentence,
    'with typos': perturb_typos,
}


def save_confusion_matrix(y_true, y_pred, labels, path):
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    size = max(8, len(labels) * 0.32)

    fig, axis = plt.subplots(figsize=(size, size))
    axis.imshow(matrix, cmap='Blues', interpolation='nearest')
    axis.set_title('MediMind confusion matrix (held-out test set)', pad=16)
    axis.set_xlabel('Predicted condition')
    axis.set_ylabel('True condition')
    axis.set_xticks(range(len(labels)))
    axis.set_yticks(range(len(labels)))
    axis.set_xticklabels(labels, rotation=90, fontsize=6)
    axis.set_yticklabels(labels, fontsize=6)

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def confidence_audit(model, x_test, y_test, threshold=0.25):
    """Count confident mistakes - the dangerous failure mode for triage."""
    probabilities = model.predict_proba(x_test)
    classes = model.classes_

    confident_wrong = 0
    withheld = 0
    correct_confident = 0

    for row, truth in zip(probabilities, y_test):
        best = row.argmax()
        confidence = float(row[best])
        prediction = classes[best]

        if confidence < threshold:
            withheld += 1
        elif prediction != truth:
            confident_wrong += 1
        else:
            correct_confident += 1

    total = len(y_test)
    return {
        'threshold': threshold,
        'confident_and_correct': correct_confident,
        'confident_but_wrong': confident_wrong,
        'withheld_low_confidence': withheld,
        'confident_error_rate': round(confident_wrong / total, 4),
    }


def layperson_probe(model, threshold=0.25):
    """Measure the gap between clinical vocabulary and how people actually talk.

    The training data labels symptoms as tokens like `burning_micturition` and
    `dischromic _patches`. A user types "it burns when I pee". The perturbation
    study above cannot detect that mismatch, because it only ever rearranges
    the dataset's own words. These probes are written in everyday English and
    are never trained on, so they measure the one thing that decides whether
    the model is usable by real people.
    """
    if not PROBES_PATH.exists():
        return None

    payload = json.loads(PROBES_PATH.read_text(encoding='utf-8'))
    probes = payload['probes']
    classes = list(model.classes_)

    correct = 0
    withheld = 0
    confidently_wrong = 0
    misses = []

    for probe in probes:
        row = model.predict_proba([probe['text'].lower()])[0]
        best = row.argmax()
        prediction = str(classes[best])
        confidence = float(row[best])
        expected = probe['expected'].strip()

        if prediction == expected:
            correct += 1
        else:
            misses.append(
                {
                    'text': probe['text'],
                    'expected': expected,
                    'predicted': prediction,
                    'confidence': round(confidence, 4),
                }
            )
            if confidence >= threshold:
                confidently_wrong += 1

        if confidence < threshold:
            withheld += 1

    return {
        'n_probes': len(probes),
        'top1_accuracy': round(correct / len(probes), 4),
        'confidently_wrong': confidently_wrong,
        'withheld_low_confidence': withheld,
        'misses': misses,
    }


def main():
    if not DEFAULT_OUT.exists() or DEFAULT_OUT.stat().st_size == 0:
        raise SystemExit(
            f'No trained model at {DEFAULT_OUT}. Run scripts/train_model.py first.'
        )

    model = joblib.load(DEFAULT_OUT)
    texts, labels = load_dataset(DEFAULT_DATA)

    # Same split as training, so the test set really is held out.
    _, x_test, _, y_test = train_test_split(
        texts, labels, test_size=0.2, stratify=labels, random_state=RANDOM_STATE
    )

    y_pred = model.predict(x_test)
    clean_accuracy = accuracy_score(y_test, y_pred)

    print(f'Clean test accuracy: {clean_accuracy:.4f}\n')
    report = classification_report(y_test, y_pred, zero_division=0)
    print(report)

    class_labels = sorted(set(labels))
    matrix_path = save_confusion_matrix(
        y_test, y_pred, class_labels, REPORTS_DIR / 'confusion_matrix.png'
    )
    print(f'Confusion matrix saved to {matrix_path}')

    print('\nRobustness under realistic input:')
    rng = random.Random(RANDOM_STATE)
    robustness = {}
    for name, perturb in PERTURBATIONS.items():
        perturbed = [perturb(text, rng) for text in x_test]
        score = accuracy_score(y_test, model.predict(perturbed))
        robustness[name] = round(float(score), 4)
        delta = score - clean_accuracy
        print(f'  {name:32} {score:.4f}  ({delta:+.4f} vs clean)')

    audit = confidence_audit(model, x_test, y_test)
    print('\nConfidence audit at the production threshold:')
    print(f'  Confident and correct: {audit["confident_and_correct"]}')
    print(f'  Confident but wrong:   {audit["confident_but_wrong"]}')
    print(f'  Withheld (low conf.):  {audit["withheld_low_confidence"]}')

    probe = layperson_probe(model)
    if probe:
        print('\nLayperson vocabulary probe (everyday phrasing, never trained on):')
        print(
            f'  Top-1 accuracy:      {probe["top1_accuracy"]:.4f} '
            f'over {probe["n_probes"]} probes'
        )
        print(f'  Confidently wrong:   {probe["confidently_wrong"]}')
        print(f'  Withheld (low conf): {probe["withheld_low_confidence"]}')
        for miss in probe['misses']:
            print(
                f'    MISS  expected {miss["expected"]!r}, '
                f'got {miss["predicted"]!r} at {miss["confidence"]:.2f}'
            )

    summary = {
        'clean_test_accuracy': round(float(clean_accuracy), 4),
        'robustness': robustness,
        'confidence_audit': audit,
        'layperson_probe': probe,
        'n_test_samples': len(y_test),
        'n_classes': len(class_labels),
    }
    (REPORTS_DIR / 'evaluation.json').write_text(
        json.dumps(summary, indent=2), encoding='utf-8'
    )
    (REPORTS_DIR / 'classification_report.txt').write_text(report, encoding='utf-8')
    print(f'\nEvaluation summary written to {REPORTS_DIR / "evaluation.json"}')


if __name__ == '__main__':
    main()
