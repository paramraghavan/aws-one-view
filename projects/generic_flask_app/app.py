#!/usr/bin/env python
"""
Minimal Flask Script Runner
Simple approach: Write to buffer, browser polls every second
"""
import os
import re
import threading
import traceback
import logging
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import sys
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')

# Configuration
CONFIG_DIR = Path(__file__).parent / 'config'
CONFIG_DIR.mkdir(exist_ok=True)

LOGS_DIR = Path(__file__).parent / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Setup logger
logger = logging.getLogger('ScriptRunner')
logger.setLevel(logging.DEBUG)

# File handler - logs to file
log_file = LOGS_DIR / f"execution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Global output buffer - everything goes here
output_buffer = []
buffer_lock = threading.Lock()

# Track if execution is running
is_running = False
running_lock = threading.Lock()


def detect_environments():
    """Detect available environments from properties files"""
    environments = set()
    if CONFIG_DIR.exists():
        for file in CONFIG_DIR.glob('*_*.properties'):
            match = re.match(r'^([a-z]+)_', file.name)
            if match:
                environments.add(match.group(1))
    return sorted(environments)


def add_output(text: str):
    """Add text to output buffer (thread-safe)"""
    global output_buffer
    with buffer_lock:
        output_buffer.append(text)


def clear_output():
    """Clear output buffer"""
    global output_buffer
    with buffer_lock:
        output_buffer = []


class BufferCapture:
    """Captures stdout and stderr to the global buffer and logs to file"""

    def __init__(self):
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def write(self, text: str):
        """Write to original stdout, buffer, and log file"""
        self.original_stdout.write(text)
        self.original_stdout.flush()

        if text and text.strip():
            line = text.rstrip()
            add_output(line)
            logger.info(line)  # Also log to file

    def flush(self):
        """Flush the original stdout"""
        self.original_stdout.flush()


class NoInputStdin:
    """Stub stdin that prevents input() calls"""
    def read(self):
        raise RuntimeError("input() is not supported. Use function parameters instead.")

    def readline(self):
        raise RuntimeError("input() is not supported. Use function parameters instead.")


def callback_myjob(password: str, files: list):
    """
    Your callback function - receives password and list of files
    All print statements and exceptions appear in browser automatically

    Args:
        password: User-provided password
        files: List of selected file absolute paths

    Example:
    ```
    def callback_myjob(password: str, files: list):
        print(f"Processing {len(files)} files")
        print(f"Password: {'*' * len(password)}")

        for idx, file_path in enumerate(files, 1):
            print(f"[{idx}/{len(files)}] {file_path}")

            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"  File size: {size} bytes")
                # result = my_function(file_path, password)
            else:
                print(f"  ✗ File not found!")

        print("✓ All files processed")
    ```
    """

    print(f"=== Job Started ===")
    print(f"Password: {'*' * len(password)}")
    print(f"Files to process: {len(files)}")
    print()

    for idx, file_path in enumerate(files, 1):
        print(f"[{idx}/{len(files)}] Processing: {file_path}")

        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            print(f"  File size: {file_size} bytes")
            # TODO: Replace with your actual processing logic
            # result = your_library.process(file_path, password)
        else:
            print(f"  ✗ File not found!")

        print()

    print("=== Job Completed ===")


def run_job(password: str, files: list):
    """Run callback_myjob in background thread with output capture"""
    global is_running

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    old_stdin = sys.stdin

    capture = BufferCapture()
    sys.stdout = capture
    sys.stderr = capture
    sys.stdin = NoInputStdin()

    try:
        with running_lock:
            is_running = True

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting execution...")
        callback_myjob(password, files)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Execution completed successfully")

    except KeyboardInterrupt:
        print("\n❌ ERROR: Execution was interrupted")

    except RuntimeError as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("💡 TIP: Pass parameters to the callback instead of using input()")

    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        print(f"\n📋 Full traceback:")
        print(traceback.format_exc())

    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        sys.stdin = old_stdin

        with running_lock:
            is_running = False


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
        global is_running

        with running_lock:
            if is_running:
                return jsonify({'success': False, 'error': 'Job already running'}), 400

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

        # Clear buffer and start job
        clear_output()
        thread = threading.Thread(target=run_job, args=(password, files), daemon=True)
        thread.start()

        return jsonify({'success': True})

    except Exception as e:
        print(f"Error in /api/ingest: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stream_event')
def stream_event():
    """Return current output buffer (browser polls this every second)"""
    with buffer_lock:
        return jsonify({
            'output': output_buffer,
            'is_running': is_running
        })


@app.route('/api/stop', methods=['POST'])
def stop_execution():
    """Signal to stop execution"""
    # Note: Actual stopping depends on callback_myjob implementation
    # For simple jobs, they'll finish naturally
    # For long-running, add checks in callback_myjob
    global is_running
    with running_lock:
        is_running = False
    add_output(">>> Execution stopped by user")
    return jsonify({'success': True})


@app.route('/api/quick-locations', methods=['GET'])
def get_quick_locations():
    """Get quick access locations"""
    locations = []
    home = os.path.expanduser('~')

    quick_dirs = {
        'Desktop': os.path.join(home, 'Desktop'),
        'Documents': os.path.join(home, 'Documents'),
        'Downloads': os.path.join(home, 'Downloads'),
    }

    for name, path in quick_dirs.items():
        if os.path.exists(path):
            locations.append({'name': name, 'path': path})

    return jsonify({'success': True, 'locations': locations})


@app.route('/api/browse-directory', methods=['POST'])
def browse_directory():
    """Browse directory contents on the server"""
    try:
        data = request.get_json()
        path = data.get('path', None)

        # If no path provided, use home directory
        if not path or path == 'null':
            path = os.path.expanduser('~')

        path = os.path.abspath(os.path.expanduser(path))

        if not os.path.exists(path):
            return jsonify({'success': False, 'error': f'Path not found: {path}'}), 404

        if not os.path.isdir(path):
            return jsonify({'success': False, 'error': 'Path is not a directory'}), 400

        items = []
        try:
            entries = os.listdir(path)
            for entry in sorted(entries, key=str.lower):
                # Skip system files that might cause issues
                if entry.startswith('.'):
                    continue

                full_path = os.path.join(path, entry)
                try:
                    is_dir = os.path.isdir(full_path)
                    size = None
                    if not is_dir:
                        try:
                            size = os.path.getsize(full_path)
                        except (OSError, PermissionError):
                            size = None

                    items.append({
                        'name': entry,
                        'path': full_path,
                        'is_directory': is_dir,
                        'size': size
                    })
                except (PermissionError, OSError):
                    continue

        except PermissionError:
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        parent = os.path.dirname(path) if path != os.path.dirname(path) else None

        return jsonify({
            'success': True,
            'current_path': path,
            'parent_path': parent,
            'items': items
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Starting Flask App (Simple Polling)")
    print("="*60)
    print(f"Running on: http://0.0.0.0:5123")
    print("Output method: Browser polls /api/stream_event every second")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=5123, debug=True, threaded=True)
