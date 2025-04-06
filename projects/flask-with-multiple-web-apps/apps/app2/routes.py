from flask import render_template, current_app
# Import the blueprint directly to avoid circular imports
from apps.app2 import app2

@app2.route('/')
def index():
    return render_template('app2/index.html', title='App 2')

@app2.route('/dashboard')
def dashboard():
    return render_template('app2/dashboard.html', title='App 2 Dashboard')