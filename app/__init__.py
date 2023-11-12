# app/__init__.py

from flask import Flask
from doctor_ai import DoctorAI
from database import Database

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

doctor = DoctorAI()
db = Database()

from app import routes
