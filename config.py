# config.py

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')


class Config:
    """Settings shared by every environment."""

    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-insecure-key')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', f"sqlite:///{BASE_DIR / 'medimind.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MODEL_PATH = BASE_DIR / os.environ.get(
        'MODEL_PATH', 'models/machine_learning_model.pkl'
    )
    # Predictions below this confidence are withheld and the user is told to
    # see a clinician instead of being shown a guess.
    MIN_CONFIDENCE = float(os.environ.get('MIN_CONFIDENCE', 0.25))


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    # Point at a path that never exists so the suite always exercises the
    # deterministic rule-based baseline. Otherwise these tests would pass or
    # fail depending on whether the developer happens to have trained a model.
    MODEL_PATH = BASE_DIR / 'models' / 'no-model-during-tests.pkl'


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    def __init__(self):
        if self.SECRET_KEY == 'dev-only-insecure-key':
            raise RuntimeError('SECRET_KEY must be set in production.')


config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
}


def get_config(name=None):
    name = name or os.environ.get('FLASK_ENV', 'development')
    return config_by_name.get(name, DevelopmentConfig)
