from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import os
import yaml
import threading
import time
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
import socket

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Default config
DEFAULT_CONFIG = {
    'processing': {
        'delay_seconds': 2,
        'log_level': 'INFO',
        'max_concurrent_files': 3
    },
    'output': {
        'show_file_content': False,
        'detailed_logging': True
    }
}


def load_config():
    """Load configuration from YAML file"""
    try:
        with open('config.yaml', 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        # Create default config if doesn't exist
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    except yaml.YAMLError as e:
        logger.error(f"Error parsing config.yaml: {e}")
        return DEFAULT_CONFIG


def save_config(config):
    """Save configuration to YAML file"""
    try:
        with open('config.yaml', 'w') as file:
            yaml.dump(config, file, default_flow_style=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving config.yaml: {e}")
        return False


def get_client_info(request):
    """Extract client information from request"""
    client_ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)

    try:
        hostname = socket.gethostbyaddr(client_ip)[0]
    except:
        hostname = "Unknown"

    user_agent = request.headers.get('User-Agent', 'Unknown')

    return {
        'ip': client_ip,
        'hostname': hostname,
        'user_agent': user_agent,
        'timestamp': datetime.now().isoformat()
    }


def process_file(filepath, filename, client_info, config):
    """
    Custom file processing script
    This is where you would add your actual processing logic
    """
    try:
        # Get file size
        file_size = os.path.getsize(filepath)

        # Log client info
        log_entry = {
            'filename': filename,
            'filepath': filepath,
            'file_size': file_size,
            'client_info': client_info,
            'status': 'processing',
            'timestamp': datetime.now().isoformat()
        }

        # Emit processing start
        socketio.emit('file_progress', {
            'filename': filename,
            'status': 'processing',
            'message': f"Processing {filename} ({file_size:,} bytes)..."
        })

        # Log to file
        logger.info(f"Processing file: {filename}, Size: {file_size} bytes, Client: {client_info['ip']}")

        # Simulate processing time based on file size (you can replace this with actual processing)
        processing_delay = config.get('processing', {}).get('delay_seconds', 2)

        # For demo purposes, we'll simulate longer processing for larger files
        if file_size > 10 * 1024 * 1024:  # Files > 10MB
            processing_delay *= 2

        time.sleep(processing_delay)

        # Custom processing logic would go here
        # For now, we'll just print file information
        processing_result = {
            'filename': filename,
            'file_size': file_size,
            'file_path': filepath,
            'processed_at': datetime.now().isoformat(),
            'client_ip': client_info['ip'],
            'client_hostname': client_info['hostname']
        }

        # Update log entry
        log_entry['status'] = 'completed'
        log_entry['result'] = processing_result

        # Emit completion
        socketio.emit('file_progress', {
            'filename': filename,
            'status': 'completed',
            'message': f"✓ Completed {filename} ({file_size:,} bytes)",
            'result': processing_result
        })

        # Log completion
        logger.info(f"Completed processing: {filename}")

        return True, processing_result

    except Exception as e:
        error_msg = f"Error processing {filename}: {str(e)}"
        logger.error(error_msg)

        socketio.emit('file_progress', {
            'filename': filename,
            'status': 'error',
            'message': f"✗ Error: {filename} - {str(e)}"
        })

        return False, {'error': str(e)}


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/config')
def config_page():
    """Configuration page"""
    config = load_config()
    return render_template('config.html', config=yaml.dump(config, default_flow_style=False))


@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file upload and processing"""
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400

    files = request.files.getlist('files[]')
    client_info = get_client_info(request)
    config = load_config()

    # Log upload attempt
    logger.info(f"Upload request from {client_info['ip']} with {len(files)} files")

    # Create a unique session ID for this upload batch
    session_id = datetime.now().strftime('%Y%m%d_%H%M%S')

    def process_files_async():
        for file in files:
            if file.filename == '':
                continue

            filename = secure_filename(file.filename)
            if filename:
                # Save file
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{session_id}_{filename}")
                file.save(filepath)

                # Process file
                success, result = process_file(filepath, filename, client_info, config)

                # Optionally clean up file after processing
                # os.remove(filepath)

    # Start processing in background thread
    thread = threading.Thread(target=process_files_async)
    thread.daemon = True
    thread.start()

    return jsonify({
        'message': f'Upload started for {len(files)} files',
        'session_id': session_id
    })


@app.route('/config/update', methods=['POST'])
def update_config():
    """Update configuration"""
    try:
        config_text = request.json.get('config', '')
        config = yaml.safe_load(config_text)

        if save_config(config):
            return jsonify({'success': True, 'message': 'Configuration updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Error saving configuration'}), 500

    except yaml.YAMLError as e:
        return jsonify({'success': False, 'message': f'Invalid YAML: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500


@app.route('/logs')
def view_logs():
    """View application logs"""
    try:
        with open('app.log', 'r') as f:
            logs = f.read()
        return jsonify({'logs': logs})
    except FileNotFoundError:
        return jsonify({'logs': 'No log file found'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'message': 'Connected to server'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')


if __name__ == '__main__':
    # Create default config if it doesn't exist
    if not os.path.exists('config.yaml'):
        save_config(DEFAULT_CONFIG)

    print("Starting Flask application...")
    print("Access the application at: http://localhost:5001")
    print("Configuration page at: http://localhost:5001/config")

    socketio.run(app, debug=True, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True )
