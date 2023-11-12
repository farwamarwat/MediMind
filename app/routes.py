# app/routes.py

from app import app, doctor, db
from flask import render_template, request, session, redirect, url_for

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Handle user login
        username = request.form['username']
        password = request.form['password']
        # Check user credentials and set session variables
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        # Load user data from the database
        user_data = db.retrieve_user_data(session['user_id'])
        return render_template('dashboard.html', user_data=user_data)
    return redirect(url_for('login'))

@app.route('/consultation', methods=['GET', 'POST'])
def consultation():
    if 'user_id' in session:
        if request.method == 'POST':
            symptoms = request.form['symptoms']
            # Call the AI model to analyze symptoms and suggest medicines
            result = doctor.analyze_symptoms(symptoms)
            return render_template('consultation_result.html', result=result)
        return render_template('consultation.html')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))
