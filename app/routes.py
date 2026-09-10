# app/routes.py

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app import doctor
from app.models import Consultation
from database import db, retrieve_consultation_data
from triage import TriageLevel

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    consultations = retrieve_consultation_data(current_user.id, limit=5)
    total = current_user.consultations.count()
    return render_template(
        'dashboard.html',
        consultations=consultations,
        total_consultations=total,
    )


@main_bp.route('/consultation', methods=['GET', 'POST'])
@login_required
def consultation():
    if request.method == 'POST':
        symptoms = (request.form.get('symptoms') or '').strip()

        if len(symptoms) < 10:
            flash(
                'Please describe your symptoms in a little more detail '
                '(at least 10 characters).',
                'warning',
            )
            return render_template('consultation.html', symptoms=symptoms)

        result = doctor.analyze_symptoms(symptoms)

        record = Consultation(
            user_id=current_user.id,
            symptoms_text=symptoms,
            predicted_condition=result['condition'],
            confidence=result['confidence'],
            triage_level=result['triage_level'],
            advice=result['advice'],
        )
        db.session.add(record)
        db.session.commit()

        # Redirect after POST so a refresh does not re-submit the symptoms.
        return redirect(url_for('main.consultation_result', consultation_id=record.id))

    return render_template('consultation.html', symptoms='')


@main_bp.route('/consultation/<int:consultation_id>')
@login_required
def consultation_result(consultation_id):
    record = db.session.get(Consultation, consultation_id)
    if record is None:
        abort(404)
    if record.user_id != current_user.id:
        # Someone else's consultation: report it as missing, not as forbidden.
        abort(404)

    return render_template(
        'consultation_result.html', consultation=record, levels=TriageLevel
    )


@main_bp.route('/history')
@login_required
def history():
    consultations = retrieve_consultation_data(current_user.id)
    return render_template('history.html', consultations=consultations)
