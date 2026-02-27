#!/usr/bin/env python
"""
Minimal Flask Script Runner
Runs a callback function with password and selected files
"""
import os
import re
import threading
import uuid
import signal
import traceback
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit, join_room
from dotenv import load_dotenv
import sys
from io import StringIO
from datetime import datetime

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
    All print statements are captured and sent to the UI in real-time

    Args:
        password: User-provided password (str)
        files: List of selected file names (list)
        execution_id: Unique execution ID (str)

    IMPORTANT:
    - All print() statements appear on the app screen in real-time
    - If you raise an exception, it will be caught and displayed with traceback
    - Do NOT use input() - it will raise an error (pass params instead)
    - To stop early, check if execution_id still in active_executions
    - All output is visible to the user, never log sensitive data

    Example callback with error handling:
    ```
    def callback_myjob(password: str, files: list, execution_id: str):
        print(f"Processing {len(files)} files")

        for idx, filename in enumerate(files, 1):
            # Check if user clicked Stop
            if execution_id not in active_executions:
                print("Execution stopped")
                return

            print(f"[{idx}/{len(files)}] {filename}")
            try:
                result = my_library.process(filename, password)
                print(f"  ✓ Success: {result}")
            except Exception as e:
                print(f"  ✗ Failed: {e}")
                # Continue with next file or raise to stop
                raise  # This will show error on UI

        print("✓ All files processed")
    ```
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


class RealtimeOutputCapture:
    """Captures stdout and emits each line via SocketIO in real-time"""

    def __init__(self, execution_id: str):
        self.execution_id = execution_id
        self.room = f"exec_{execution_id}"
        self.original_stdout = sys.stdout

    def write(self, text: str):
        """Write text and emit to SocketIO immediately"""
        # Also write to original stdout for logging
        self.original_stdout.write(text)
        self.original_stdout.flush()

        # Emit each line to the browser
        if text and text.strip():
            try:
                socketio.emit('output', {'data': text.rstrip()}, room=self.room)
            except Exception as e:
                # If emit fails, log to console for debugging
                self.original_stdout.write(f"\n[DEBUG] SocketIO emit failed: {e}\n")
                self.original_stdout.flush()

    def flush(self):
        """Flush the original stdout"""
        self.original_stdout.flush()


class NoInputStdin:
    """Stub stdin that prevents input() calls"""
    def read(self):
        raise RuntimeError("input() is not supported in web callbacks. Use function parameters instead.")

    def readline(self):
        raise RuntimeError("input() is not supported in web callbacks. Use function parameters instead.")


def capture_callback_output(password: str, files: list, execution_id: str):
    """Capture stdout from callback_myjob and emit via SocketIO in real-time"""

    old_stdout = sys.stdout
    old_stdin = sys.stdin

    # DEBUG: Log to console that we're starting
    print(f"[BACKEND DEBUG] Starting capture_callback_output for execution_id={execution_id}")
    print(f"[BACKEND DEBUG] Files: {files}")
    print(f"[BACKEND DEBUG] Room: exec_{execution_id}")

    capture = RealtimeOutputCapture(execution_id)
    sys.stdout = capture
    sys.stdin = NoInputStdin()  # Prevent input() calls

    error_occurred = False

    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting execution...")
        print(f"[DEBUG] Calling callback_myjob with {len(files)} file(s)")

        callback_myjob(password, files, execution_id)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Execution completed successfully")

    except KeyboardInterrupt:
        error_occurred = True
        print("\n❌ ERROR: Execution was interrupted by user")

    except RuntimeError as e:
        # Likely an input() call attempt
        error_occurred = True
        print(f"\n❌ ERROR: {str(e)}")
        print("\n💡 TIP: Pass parameters to the callback instead of using input()")
        print("   Example: use 'password' and 'files' parameters directly")

    except Exception as e:
        error_occurred = True
        print(f"\n❌ ERROR: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        print(f"\n📋 Full traceback:")
        print(traceback.format_exc())

    finally:
        sys.stdout = old_stdout
        sys.stdin = old_stdin

    # DEBUG: Log to console that we're done
    print(f"[BACKEND DEBUG] Execution finished. Error occurred: {error_occurred}")

    # Mark execution as complete with status
    room = f"exec_{execution_id}"
    print(f"[BACKEND DEBUG] Emitting 'complete' event to room: {room}")

    try:
        socketio.emit('complete', {
            'status': 'error' if error_occurred else 'completed',
            'timestamp': datetime.now().isoformat()
        }, room=room)
        print(f"[BACKEND DEBUG] 'complete' event emitted successfully")
    except Exception as e:
        print(f"[BACKEND DEBUG] Failed to emit 'complete' event: {e}")

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

        print(f"\n[BACKEND DEBUG] /api/ingest called")
        print(f"[BACKEND DEBUG] Password length: {len(password)}")
        print(f"[BACKEND DEBUG] Files: {files}")
        print(f"[BACKEND DEBUG] Environment: {environment}")

        if not password:
            return jsonify({'success': False, 'error': 'Password required'}), 400

        if not files:
            return jsonify({'success': False, 'error': 'No files selected'}), 400

        if not environment:
            return jsonify({'success': False, 'error': 'Environment required'}), 400

        # Generate execution ID
        execution_id = str(uuid.uuid4())
        room = f"exec_{execution_id}"

        print(f"[BACKEND DEBUG] Generated execution_id: {execution_id}")
        print(f"[BACKEND DEBUG] Room: {room}")

        # Store execution info
        active_executions[execution_id] = {
            'status': 'running',
            'environment': environment
        }

        # Store password in session for this environment
        session[f'password_{environment}'] = password
        session.modified = True

        # Start execution in background thread
        print(f"[BACKEND DEBUG] Starting background thread...")
        thread = threading.Thread(
            target=capture_callback_output,
            args=(password, files, execution_id),
            daemon=True
        )
        thread.start()

        print(f"[BACKEND DEBUG] Thread started successfully")

        return jsonify({
            'success': True,
            'execution_id': execution_id
        })

    except Exception as e:
        print(f"[BACKEND DEBUG] Exception in /api/ingest: {e}")
        print(traceback.format_exc())
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
