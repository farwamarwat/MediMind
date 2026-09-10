# MediMind

**Symptom triage for people who cannot always reach a doctor quickly.**

MediMind reads a symptom description written in plain language and answers the
question that matters most before any diagnosis: *how urgently should this
person seek human care?* It returns a triage level, an optional likely
condition with an explicit confidence score, and guidance on what to do next.

Originally built as a final year project addressing healthcare accessibility in
Pakistan, where long waiting times and thin primary-care coverage mean people
often decide alone whether a symptom is worth a clinic visit.

> **MediMind is not a doctor.** It does not diagnose and it does not prescribe.
> It is a triage aid that points people toward appropriate care. See
> [Safety design](#safety-design) for how that boundary is enforced in code.

---

## Why triage, not diagnosis

Most student symptom checkers try to name a disease and suggest a medicine.
That is the wrong target: it is the part a model is least reliable at, and the
part where being wrong does the most harm.

MediMind inverts it. Naming the condition is optional and always carries a
confidence score. Deciding **how fast to act** is mandatory and never depends on
the model alone.

| Triage level | Meaning |
| --- | --- |
| `self_care` | Manageable at home |
| `see_doctor` | See a doctor within a few days |
| `urgent` | Seek care within 24 hours |
| `emergency` | Go to a hospital now |

## Safety design

Three rules hold regardless of what the classifier predicts:

1. **Red flags bypass the model entirely.** Chest pain, difficulty breathing,
   coughing blood, loss of consciousness, seizures, stroke signs and other
   emergency indicators are matched deterministically in
   [`doctor_ai.py`](doctor_ai.py) and escalate straight to `emergency`. No
   model output can downgrade them.
2. **Low confidence produces no guess.** Below `MIN_CONFIDENCE` the app says it
   does not know and routes the user to a clinician, rather than showing its
   best guess as if it were an answer.
3. **No medicine is ever named.** Care guidance is deliberately general and
   defers drug choices to a pharmacist or doctor.

These rules are covered by tests in
[`tests/test_triage.py`](tests/test_triage.py), including one asserting that
advice text never contains a drug name.

## Features

- Free-text symptom entry, no rigid checkbox questionnaire
- Deterministic emergency red-flag detection, independent of the ML model
- Condition suggestion with a visible confidence bar
- Account signup and login with hashed passwords and session management
- Per-user consultation history, with results readable only by their owner
- Client-side emergency warning that appears as the user types
- Structured logging and custom error pages

## Tech stack

| Layer | Choice |
| --- | --- |
| Web | Flask 3, Jinja2, blueprints, application factory |
| Auth | Flask-Login, Flask-WTF, Werkzeug password hashing |
| Data | SQLAlchemy 2, SQLite (Postgres-ready via `DATABASE_URL`) |
| ML | scikit-learn, joblib |
| Tests | pytest |
| Serving | Gunicorn behind nginx |

## Getting started

```bash
git clone https://github.com/farwamarwat/MediMind.git
cd MediMind

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # then set SECRET_KEY
python run.py
```

The app runs at <http://127.0.0.1:5000>. The database is created automatically
on first start.

No trained model is required to run MediMind: with `models/` empty it falls
back to a documented rule-based baseline so a fresh clone works immediately.

### Configuration

All settings come from the environment, documented in
[`.env.example`](.env.example):

| Variable | Purpose |
| --- | --- |
| `SECRET_KEY` | Session signing key. Required in production. |
| `DATABASE_URL` | SQLAlchemy connection string. Defaults to local SQLite. |
| `MODEL_PATH` | Location of the trained classifier. |
| `MIN_CONFIDENCE` | Confidence floor below which no condition is shown. |

### Running the tests

```bash
pytest
```

## Project structure

```
MediMind/
├── app/
│   ├── __init__.py          # application factory
│   ├── routes.py            # main blueprint
│   ├── models.py            # Consultation model
│   ├── auth/                # signup, login, User model, forms
│   ├── templates/
│   └── static/
├── config.py                # environment-driven configuration
├── database.py              # SQLAlchemy instance and data access
├── doctor_ai.py             # triage engine: red flags + classifier
├── triage.py                # shared triage vocabulary
├── tests/
├── nginx/                   # reverse proxy config
└── run.py                   # entry point
```

## Roadmap

- [x] Working authentication, persistence and consultation flow
- [x] Red-flag triage layer with test coverage
- [ ] Trained symptom classifier with published evaluation metrics
- [ ] Urdu/English bilingual interface
- [ ] SMS access for users without smartphones
- [ ] Anonymised aggregate symptom trends dashboard
- [ ] Continuous integration and a deployed public demo

## Team

MediMind began as a three-person final year project:

- **Farwa Khan** ([@farwamarwat](https://github.com/farwamarwat))
- **Haris Afzal** ([@HarisAfzal7](https://github.com/HarisAfzal7))
- _third team member - name and GitHub handle to be added_

The v1.0 release was the team's original project. Work from v2.0 onward is a
continuation by Farwa Khan.

## Disclaimer

MediMind provides general health information only. It is not a substitute for
professional medical advice, diagnosis or treatment. Never disregard
professional medical advice or delay seeking it because of something you read
here. In an emergency in Pakistan, call **Rescue 1122**.

## License

Released under the [MIT License](LICENSE).
