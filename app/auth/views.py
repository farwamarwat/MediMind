# app/auth/views.py

from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.auth.forms import LoginForm, SignupForm
from app.auth.models import User
from database import db

auth_bp = Blueprint('auth', __name__)


def _safe_redirect_target(target, fallback):
    """Only follow `next` when it points back at this site."""
    if not target:
        return fallback
    parsed = urlparse(target)
    if parsed.netloc or parsed.scheme:
        return fallback
    return target


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = SignupForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data.lower(),
            full_name=form.full_name.data or None,
            age=form.age.data,
            gender=form.gender.data or None,
            city=form.city.data or None,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash('Account created. Welcome to MediMind.', 'success')
        return redirect(url_for('main.dashboard'))

    return render_template('signup.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(
            db.select(User).where(User.username == form.username.data)
        )
        # Deliberately vague: never reveal whether the username exists.
        if user is None or not user.check_password(form.password.data):
            flash('Incorrect username or password.', 'danger')
            return render_template('login.html', form=form)

        login_user(user, remember=form.remember_me.data)
        destination = _safe_redirect_target(
            request.args.get('next'), url_for('main.dashboard')
        )
        return redirect(destination)

    return render_template('login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been signed out.', 'info')
    return redirect(url_for('main.index'))
