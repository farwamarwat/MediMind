# app/auth/forms.py

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
    Optional,
    Regexp,
    ValidationError,
)

from database import db


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Keep me signed in')
    submit = SubmitField('Log in')


class SignupForm(FlaskForm):
    username = StringField(
        'Username',
        validators=[
            DataRequired(),
            Length(min=3, max=64),
            Regexp(
                r'^[A-Za-z0-9_.-]+$',
                message='Letters, numbers, dots, dashes and underscores only.',
            ),
        ],
    )
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    full_name = StringField('Full name', validators=[Optional(), Length(max=120)])
    age = IntegerField('Age', validators=[Optional(), NumberRange(min=1, max=120)])
    gender = SelectField(
        'Gender',
        choices=[
            ('', 'Prefer not to say'),
            ('female', 'Female'),
            ('male', 'Male'),
            ('other', 'Other'),
        ],
        validators=[Optional()],
    )
    city = StringField('City', validators=[Optional(), Length(max=80)])
    password = PasswordField(
        'Password',
        validators=[
            DataRequired(),
            Length(min=8, message='Use at least 8 characters.'),
        ],
    )
    confirm_password = PasswordField(
        'Confirm password',
        validators=[DataRequired(), EqualTo('password', message='Passwords must match.')],
    )
    submit = SubmitField('Create account')

    def validate_username(self, field):
        from app.auth.models import User

        existing = db.session.scalar(
            db.select(User).where(User.username == field.data)
        )
        if existing:
            raise ValidationError('That username is already taken.')

    def validate_email(self, field):
        from app.auth.models import User

        existing = db.session.scalar(
            db.select(User).where(User.email == field.data.lower())
        )
        if existing:
            raise ValidationError('An account with that email already exists.')
