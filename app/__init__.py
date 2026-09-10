# app/__init__.py

import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template
from flask_login import LoginManager

from config import BASE_DIR, get_config
from database import db, init_db
from doctor_ai import DoctorAI

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to continue.'
login_manager.login_message_category = 'info'

doctor = DoctorAI()


def create_app(config_name=None):
    """Build and configure a MediMind application instance."""
    app = Flask(__name__)
    app.config.from_object(get_config(config_name)())

    init_db(app)
    login_manager.init_app(app)
    _configure_logging(app)

    # The triage engine is process-wide, but its settings come from config.
    doctor.model_path = app.config['MODEL_PATH']
    doctor.min_confidence = app.config['MIN_CONFIDENCE']
    doctor.load_model()

    from app.auth.views import auth_bp
    from app.routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    _register_error_handlers(app)
    _register_context_processors(app)

    app.logger.info('MediMind started in %s mode', app.config.get('ENV', 'development'))
    return app


@login_manager.user_loader
def load_user(user_id):
    from app.auth.models import User

    return db.session.get(User, int(user_id))


def _configure_logging(app):
    if app.config.get('TESTING'):
        return

    log_dir = BASE_DIR / 'logs'
    log_dir.mkdir(exist_ok=True)

    handler = RotatingFileHandler(
        log_dir / 'medimind.log', maxBytes=1_000_000, backupCount=5
    )
    handler.setFormatter(
        logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    )
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)


def _register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        app.logger.exception('Unhandled server error')
        return render_template('errors/500.html'), 500


def _register_context_processors(app):
    @app.context_processor
    def inject_globals():
        return {'now_year': datetime.now(timezone.utc).year}
