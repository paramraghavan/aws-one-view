from flask import render_template, current_app
# Import the blueprint directly to avoid circular imports
from apps.app1 import app1


@app1.route('/')
def index():
    return render_template('app1/index.html', title='App 1')

@app1.route('/feature')
def feature():
    return render_template('app1/feature.html', title='App 1 Feature')
