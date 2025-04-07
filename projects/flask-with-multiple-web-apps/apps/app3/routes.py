from flask import render_template, jsonify, current_app
# Import the blueprint directly to avoid circular imports
from apps.app3 import app3

@app3.route('/')
def index():
    return render_template('app3/index.html', title='App 3')

@app3.route('/api/data')
def api_data():
    data = {
        'name': 'App 3 API',
        'version': '1.0.0',
        'endpoints': ['api/data', 'api/users']
    }
    return jsonify(data)
