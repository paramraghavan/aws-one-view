#!/usr/bin/env python
"""
Minimal Flask Script Runner
Runs a callback function with password and selected files
"""
import os
import re
import threading
import uuid
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room
from dotenv import load_dotenv
import sys
from io import StringIO

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
CONFIG_DIR = Path('config')
CONFIG_DIR.mkdir(exist_ok=True)

# Active execution tracking
active_executions = {}


def detect_environments():
    """Detect available environments from properties files"""
    environments = set()
    if CONFIG_DIR.exists():
        for file in CONFIG_DIR.glob('*_*.properties'):
            # Extract environment name from prefix (e.g., uat_app.properties -> uat)
            match = re.match(r'^([a-z]+)_', file.name)
            if match:
                environments.add(match.group(1))
    return sorted(environments)


def callback_myjob(password: str, files: list, execution_id: str):
    """
    Your callback function - receives password and list of files
    All print statements will be captured and sent to the UI

    Args:
        password: User-provided password
        files: List of selected file paths
        execution_id: Unique execution ID for SocketIO room
    """

    print(f"=== Job Started ===")
    print(f"Password: {'*' * len(password)}")
    print(f"Files to process: {len(files)}")
    print()

    for idx, file_path in enumerate(files, 1):
        if execution_id not in active_executions:
            print("Execution stopped by user")
            break

        print(f"Processing file {idx}/{len(files)}: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")

        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"File size: {file_size} bytes")

        print()

    print("=== Job Completed ===")


def capture_callback_output(password: str, files: list, execution_id: str):
    """Capture stdout from callback_myjob and emit via SocketIO"""

    # Redirect stdout to capture prints
    old_stdout = sys.stdout
    sys.stdout = StringIO()

    try:
        callback_myjob(password, files, execution_id)
        output = sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout

    # Emit output line by line
    for line in output.split('\n'):
        if line.strip():
            socketio.emit('output', {'data': line}, room=f"exec_{execution_id}")

    # Mark execution as complete
    socketio.emit('complete', {'status': 'completed'}, room=f"exec_{execution_id}")

    if execution_id in active_executions:
        del active_executions[execution_id]


# ============== Routes ==============

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/environments')
def get_environments():
    """Get available environments from config files"""
    environments = detect_environments()
    return jsonify(environments)


@app.route('/api/ingest', methods=['POST'])
def ingest():
    """Start job execution"""
    try:
        data = request.get_json()
        password = data.get('password', '')
        files = data.get('files', [])
        environment = data.get('environment', '')

        if not password:
            return jsonify({'success': False, 'error': 'Password required'}), 400

        if not files:
            return jsonify({'success': False, 'error': 'No files selected'}), 400

        if not environment:
            return jsonify({'success': False, 'error': 'Environment required'}), 400

        # Generate execution ID
        execution_id = str(uuid.uuid4())
        room = f"exec_{execution_id}"

        # Store execution info
        active_executions[execution_id] = {
            'status': 'running',
            'environment': environment
        }

        # Store password in session for this environment
        session[f'password_{environment}'] = password
        session.modified = True

        # Start execution in background thread
        thread = threading.Thread(
            target=capture_callback_output,
            args=(password, files, execution_id),
            daemon=True
        )
        thread.start()

        return jsonify({
            'success': True,
            'execution_id': execution_id
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stop/<execution_id>', methods=['POST'])
def stop_execution(execution_id):
    """Stop current execution"""
    if execution_id in active_executions:
        del active_executions[execution_id]
        room = f"exec_{execution_id}"
        socketio.emit('output', {'data': '>>> Execution stopped by user'}, room=room)
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Execution not found'}), 404


@app.route('/api/get-password/<environment>')
def get_password(environment):
    """Get cached password for environment if available"""
    cached_password = session.get(f'password_{environment}', '')
    return jsonify({'has_password': bool(cached_password)})


@app.route('/api/clear-password/<environment>', methods=['POST'])
def clear_password(environment):
    """Clear cached password for environment"""
    session.pop(f'password_{environment}', None)
    session.modified = True
    return jsonify({'success': True})


# ============== SocketIO Events ==============

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f"Client connected: {request.sid}")


@socketio.on('join_execution')
def on_join_execution(data):
    """Join execution room for real-time updates"""
    execution_id = data.get('execution_id')
    room = f"exec_{execution_id}"
    join_room(room)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5123, debug=True)
