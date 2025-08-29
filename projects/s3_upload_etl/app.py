from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_socketio import SocketIO, emit
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import json
import os
import logging
from datetime import datetime, timezone
from cryptography.fernet import Fernet
import base64
import hashlib
from werkzeug.utils import secure_filename
import subprocess
import sys
from threading import Thread
import time

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'fallback-secret-key-change-this')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_UPLOAD_SIZE', 100 * 1024 * 1024))  # Default 100MB

# Initialize SocketIO for real-time logging
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration file path
CONFIG_FILE = 'config.json'
ENCRYPTED_PASS_FILE = '.encrypted_pass'
UPLOAD_FOLDER = 'temp_uploads'

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LogHandler(logging.Handler):
    """Custom log handler to emit logs via SocketIO"""

    def emit(self, record):
        log_entry = self.format(record)
        socketio.emit('log_message', {'message': log_entry, 'timestamp': datetime.now().isoformat()})


# Add custom log handler
log_handler = LogHandler()
log_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)

# Also add handler to boto3 logger
boto3_logger = logging.getLogger('boto3')
boto3_logger.addHandler(log_handler)
boto3_logger.setLevel(logging.INFO)

botocore_logger = logging.getLogger('botocore')
botocore_logger.addHandler(log_handler)
botocore_logger.setLevel(logging.INFO)


def load_config():
    """Load configuration from file"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Default configuration
        config = {
            'aws_script_path': './get_aws_tokens.py',
            'default_bucket': 'my-default-bucket',
            'available_buckets': ['my-default-bucket', 'another-bucket'],
            'aws_region': 'us-east-1'
        }
        save_config(config)
        return config


def save_config(config):
    """Save configuration to file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, indent=2, fp=f)


def get_encryption_key():
    """Generate or load encryption key"""
    key_file = '.encryption_key'
    if os.path.exists(key_file):
        with open(key_file, 'rb') as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(key)
        return key


def encrypt_password(password):
    """Encrypt password"""
    key = get_encryption_key()
    f = Fernet(key)
    encrypted = f.encrypt(password.encode())
    with open(ENCRYPTED_PASS_FILE, 'wb') as file:
        file.write(encrypted)


def decrypt_password():
    """Decrypt password"""
    if not os.path.exists(ENCRYPTED_PASS_FILE):
        return None

    key = get_encryption_key()
    f = Fernet(key)

    with open(ENCRYPTED_PASS_FILE, 'rb') as file:
        encrypted = file.read()

    try:
        decrypted = f.decrypt(encrypted)
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Error decrypting password: {e}")
        return None


def run_aws_token_script(password):
    """Run the AWS token script with password and capture all output"""
    config = load_config()
    script_path = config.get('aws_script_path', './get_aws_tokens.py')

    try:
        logger.info("Running AWS token script...")
        logger.info(f"Script path: {script_path}")

        # Run the script with password input
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )

        # Send password and get output
        stdout, stderr = process.communicate(input=password + '\n', timeout=30)

        # Log all script output line by line
        if stdout:
            logger.info("=== AWS Token Script Output ===")
            for line in stdout.strip().split('\n'):
                if line.strip():
                    logger.info(f"SCRIPT: {line}")
            logger.info("=== End Script Output ===")

        if stderr:
            logger.warning("=== AWS Token Script Errors ===")
            for line in stderr.strip().split('\n'):
                if line.strip():
                    logger.warning(f"SCRIPT ERROR: {line}")
            logger.warning("=== End Script Errors ===")

        if process.returncode == 0:
            logger.info("AWS token script completed successfully")
            return True, stdout
        else:
            logger.error(f"AWS token script failed with return code: {process.returncode}")
            return False, stderr

    except subprocess.TimeoutExpired:
        logger.error("AWS token script timed out after 30 seconds")
        process.kill()
        return False, "Script timeout"
    except FileNotFoundError:
        logger.error(f"AWS token script not found: {script_path}")
        return False, f"Script not found: {script_path}"
    except Exception as e:
        logger.error(f"Error running AWS token script: {e}")
        return False, str(e)


def get_s3_client():
    """Get configured S3 client"""
    try:
        # Use default credential chain (environment variables, IAM roles, etc.)
        s3_client = boto3.client('s3', region_name=load_config().get('aws_region', 'us-east-1'))
        return s3_client
    except Exception as e:
        logger.error(f"Error creating S3 client: {e}")
        return None


def list_s3_objects(bucket_name, page=1, per_page=10):
    """List S3 objects with pagination"""
    s3_client = get_s3_client()
    if not s3_client:
        return [], 0

    try:
        logger.info(f"Listing objects from bucket: {bucket_name}")

        # List all objects first to get total count
        all_objects = []
        paginator = s3_client.get_paginator('list_objects_v2')

        for page_obj in paginator.paginate(Bucket=bucket_name):
            if 'Contents' in page_obj:
                all_objects.extend(page_obj['Contents'])

        # Sort by LastModified in descending order
        all_objects.sort(key=lambda x: x['LastModified'], reverse=True)

        # Calculate pagination
        total_objects = len(all_objects)
        start_index = (page - 1) * per_page
        end_index = start_index + per_page

        paginated_objects = all_objects[start_index:end_index]

        # Format objects for display
        formatted_objects = []
        for obj in paginated_objects:
            formatted_objects.append({
                'key': obj['Key'],
                'last_modified': obj['LastModified'].isoformat(),
                'size': obj['Size'],
                'etag': obj['ETag'].strip('"')
            })

        return formatted_objects, total_objects

    except ClientError as e:
        logger.error(f"Error listing S3 objects: {e}")
        return [], 0


def upload_to_s3(file_path, bucket_name, key_name):
    """Upload file to S3 with detailed logging"""
    s3_client = get_s3_client()
    if not s3_client:
        return False, "S3 client not available"

    try:
        logger.info(f"Starting upload: {file_path} -> s3://{bucket_name}/{key_name}")

        # Get file size for progress tracking
        file_size = os.path.getsize(file_path)
        logger.info(f"File size: {file_size} bytes")

        # Upload file
        s3_client.upload_file(
            file_path,
            bucket_name,
            key_name,
            ExtraArgs={'ServerSideEncryption': 'AES256'}
        )

        logger.info(f"Successfully uploaded {key_name} to {bucket_name}")
        return True, "Upload successful"

    except ClientError as e:
        error_msg = f"AWS error uploading file: {e}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected error uploading file: {e}"
        logger.error(error_msg)
        return False, error_msg


@app.route('/')
def index():
    """Main page"""
    if 'authenticated' not in session:
        return redirect(url_for('login'))

    config = load_config()
    return render_template('index.html', config=config)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        password = request.form.get('password')

        # Generate session ID for logging
        session_id = hashlib.md5(f"{datetime.now().isoformat()}{password[:5]}".encode()).hexdigest()[:8]

        # Check if this is first login or password verification
        stored_password = decrypt_password()

        if stored_password is None:
            # First time login - store password and run script
            logger.info(f"First-time login attempt for session: {session_id}")
            success, message = run_aws_token_script(password)
            if success:
                encrypt_password(password)
                session['authenticated'] = True
                session['session_id'] = session_id
                session['login_time'] = datetime.now().isoformat()
                logger.info(f"First-time setup completed for session: {session_id}")
                flash('Password saved and AWS tokens retrieved successfully!', 'success')
                return redirect(url_for('index'))
            else:
                logger.error(f"First-time setup failed for session: {session_id}")
                flash(f'Failed to get AWS tokens: {message}', 'error')
        else:
            # Verify existing password
            logger.info(f"Login attempt for session: {session_id}")
            if password == stored_password:
                success, message = run_aws_token_script(password)
                if success:
                    session['authenticated'] = True
                    session['session_id'] = session_id
                    session['login_time'] = datetime.now().isoformat()
                    logger.info(f"Login successful for session: {session_id}")
                    flash('AWS tokens refreshed successfully!', 'success')
                    return redirect(url_for('index'))
                else:
                    logger.error(f"Token refresh failed for session: {session_id}")
                    flash(f'Failed to refresh AWS tokens: {message}', 'error')
            else:
                logger.warning(f"Invalid password for session: {session_id}")
                flash('Incorrect password!', 'error')

    return render_template('login.html')


@app.route('/change-password', methods=['POST'])
def change_password():
    """Change stored password"""
    if 'authenticated' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'})

    new_password = request.form.get('new_password')

    # Test new password with AWS script
    success, message = run_aws_token_script(new_password)

    if success:
        encrypt_password(new_password)
        return jsonify({'success': True, 'message': 'Password updated successfully'})
    else:
        return jsonify({'success': False, 'message': f'Password test failed: {message}'})


@app.route('/refresh-tokens', methods=['POST'])
def refresh_tokens():
    """Manually refresh AWS tokens"""
    if 'authenticated' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'})

    password = decrypt_password()
    if not password:
        return jsonify({'success': False, 'message': 'No stored password'})

    success, message = run_aws_token_script(password)

    return jsonify({'success': success, 'message': message})


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload with detailed ETL logging"""
    if 'authenticated' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'})

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file selected'})

    file = request.files['file']
    bucket_name = request.form.get('bucket')

    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'})

    if file and bucket_name:
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"

        # Save file temporarily
        temp_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(temp_path)

        logger.info(f"File saved temporarily: {temp_path}")
        logger.info(f"Starting S3 upload process for: {filename}")

        try:
            # Use enhanced ETL upload with detailed logging
            from s3_etl_library import S3ETLProcessor

            processor = S3ETLProcessor(logger=logger)
            result = processor.upload_file_with_etl(
                file_path=temp_path,
                bucket_name=bucket_name,
                key=unique_filename,
                storage_class='STANDARD',
                tags={
                    'uploaded-by': 'flask-app',
                    'original-filename': filename,
                    'upload-timestamp': timestamp
                },
                metadata={
                    'uploaded-via': 'web-interface',
                    'user-session': session.get('session_id', 'unknown')
                }
            )

            # Clean up temp file
            try:
                os.remove(temp_path)
                logger.info(f"Temporary file cleaned up: {temp_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file: {cleanup_error}")

            if result['success']:
                return jsonify({
                    'success': True,
                    'message': f'Upload completed: {result["upload_speed_human"]} in {result["upload_duration"]:.1f}s',
                    'details': result
                })
            else:
                return jsonify({'success': False, 'message': 'Upload failed - check logs for details'})

        except Exception as e:
            logger.error(f"ETL upload process failed: {e}")
            # Fallback to basic upload
            success, message = upload_to_s3(temp_path, bucket_name, unique_filename)

            # Clean up temp file
            try:
                os.remove(temp_path)
            except:
                pass

            return jsonify({'success': success, 'message': message})

    return jsonify({'success': False, 'message': 'Invalid request'})


@app.route('/list-objects')
def list_objects():
    """List S3 objects with pagination"""
    if 'authenticated' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'})

    bucket = request.args.get('bucket')
    page = int(request.args.get('page', 1))
    per_page = 10

    if not bucket:
        return jsonify({'success': False, 'message': 'Bucket name required'})

    objects, total = list_s3_objects(bucket, page, per_page)

    return jsonify({
        'success': True,
        'objects': objects,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    })


@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    return redirect(url_for('login'))


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    session_id = session.get('session_id', 'unknown')
    logger.info(f"WebSocket client connected - Session: {session_id}")
    emit('connected', {
        'message': 'Connected to log stream',
        'session_id': session_id,
        'timestamp': datetime.now().isoformat()
    })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    session_id = session.get('session_id', 'unknown')
    logger.info(f"WebSocket client disconnected - Session: {session_id}")


@socketio.on('request_log_history')
def handle_log_history():
    """Send recent log history to newly connected client"""
    emit('log_message', {
        'message': f'Log stream initialized at {datetime.now().strftime("%H:%M:%S")}',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    # Create sample AWS token script if it doesn't exist
    script_path = './get_aws_tokens.py'
    if not os.path.exists(script_path):
        logger.info("Creating sample AWS token script...")
        sample_script = '''#!/usr/bin/env python3
import getpass
import time
import sys
import os

def get_aws_tokens():
    """Sample AWS token retrieval script"""
    print("AWS Token Retrieval Script v1.0")
    print("================================")

    password = input("Enter password: ")

    print("Authenticating with AWS...")
    time.sleep(1)  # Simulate authentication delay

    print("Validating credentials...")
    time.sleep(1)

    # Replace this logic with your actual authentication
    if password == "demo123":  # Replace with your actual logic
        print("Authentication successful!")
        print("Retrieving temporary credentials...")
        time.sleep(1)
        print("Setting environment variables...")
        print("AWS_ACCESS_KEY_ID=AKIA...")
        print("AWS_SECRET_ACCESS_KEY=***")
        print("AWS_SESSION_TOKEN=***")
        print("Retrieved AWS tokens successfully")
        return True
    else:
        print("Authentication failed!")
        print("Invalid credentials provided")
        return False

if __name__ == "__main__":
    try:
        success = get_aws_tokens()
        if success:
            print("Token retrieval completed successfully")
            sys.exit(0)
        else:
            print("Token retrieval failed")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
'''
        with open(script_path, 'w') as f:
            f.write(sample_script)
        os.chmod(script_path, 0o755)
        logger.info(f"Sample script created: {script_path}")

    logger.info("Starting Flask-SocketIO server...")
    logger.info("Application will be available at: http://localhost:5000")
    logger.info("Log outputs will be visible in the web interface")

    socketio.run(
        app,
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
        host='0.0.0.0',
        port=int(os.getenv('FLASK_PORT', 5000)),
        allow_unsafe_werkzeug=True  # For development only
    )