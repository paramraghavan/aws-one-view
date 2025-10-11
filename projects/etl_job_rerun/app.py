from flask import Flask, render_template, request, jsonify, send_file
import boto3
from botocore.exceptions import ClientError
import pandas as pd
import pickle
import os
from datetime import datetime
import json
from pathlib import Path
import re
from cleanup_hooks import CleanupHookManager
from env_config import (
    get_bucket_config,
    get_all_profiles,
    validate_profile_config,
    SNOWFLAKE_CONFIG,
    FLASK_CONFIG,
    APP_SETTINGS
)

app = Flask(__name__)
app.config['SECRET_KEY'] = FLASK_CONFIG.get('SECRET_KEY', 'your-secret-key-here')

# Configuration
CONFIG_FILE = APP_SETTINGS.get('config_file', 'entity_config.json')
PICKLE_DIR = APP_SETTINGS.get('pickle_dir', 'pickle_files')
os.makedirs(PICKLE_DIR, exist_ok=True)

# Initialize cleanup manager with Snowflake config from env_config
cleanup_manager = CleanupHookManager(SNOWFLAKE_CONFIG)


def load_entity_config():
    """Load entity mapping configuration"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_entity_config(config):
    """Save entity mapping configuration"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, indent=2, fp=f)


def get_s3_client(profile_name):
    """Create S3 client with specified AWS profile"""
    session = boto3.Session(profile_name=profile_name)
    return session.client('s3')


def parse_s3_path(s3_path):
    """Parse S3 path into bucket and prefix"""
    s3_path = s3_path.replace('s3://', '').replace('s3:\\', '')
    parts = s3_path.split('/', 1)
    bucket = parts[0]
    prefix = parts[1] if len(parts) > 1 else ''
    return bucket, prefix


def list_s3_objects(s3_client, bucket, prefix, start_date=None, end_date=None):
    """List objects in S3 bucket with optional date filtering"""
    objects = []
    paginator = s3_client.get_paginator('list_objects_v2')

    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                key = obj['Key']
                last_modified = obj['LastModified']

                # Date filtering
                if start_date and last_modified < start_date:
                    continue
                if end_date and last_modified > end_date:
                    continue

                objects.append({
                    'key': key,
                    'last_modified': last_modified,
                    'size': obj['Size']
                })
    except ClientError as e:
        print(f"Error listing objects: {e}")
        return []

    return objects


def parse_dataset_path(key):
    """Parse dataset path to extract entity, dataset, year, month, day, filename"""
    pattern = r'([^/]+)/Dataset(\d+)/year=(\d{4})/month=(\d{1,2})/day=(\d{1,2})/([^/]+)$'
    match = re.search(pattern, key)

    if match:
        return {
            'entity_name': match.group(1),
            'dataset': f'Dataset{match.group(2)}',
            'year': match.group(3),
            'month': match.group(4).zfill(2),
            'day': match.group(5).zfill(2),
            'filename': match.group(6)
        }
    return None


def create_pickle_file(s3_client, source_bucket, entities, start_date, end_date, profile_name):
    """Parse S3 bucket and create pickle file"""
    all_records = []

    for entity in entities:
        prefix = f"{entity}/"
        objects = list_s3_objects(s3_client, source_bucket, prefix, start_date, end_date)

        for obj in objects:
            parsed = parse_dataset_path(obj['key'])
            if parsed and parsed['entity_name'] == entity:
                all_records.append(parsed)

    # Create DataFrame
    df = pd.DataFrame(all_records)

    # Generate pickle filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    pickle_filename = f"{PICKLE_DIR}/datasets_{profile_name}_{timestamp}.pkl"

    # Save to pickle
    with open(pickle_filename, 'wb') as f:
        pickle.dump(df, f)

    return pickle_filename, df


def load_pickle_file(pickle_filename):
    """Load existing pickle file"""
    with open(pickle_filename, 'rb') as f:
        return pickle.load(f)


def copy_file_to_staging(s3_client, source_bucket, source_key, dest_bucket, entity_name, filename):
    """Copy file from source to staging bucket"""
    dest_key = f"stage/{entity_name}/{filename}"

    try:
        copy_source = {'Bucket': source_bucket, 'Key': source_key}
        s3_client.copy_object(
            CopySource=copy_source,
            Bucket=dest_bucket,
            Key=dest_key
        )
        return True, dest_key
    except ClientError as e:
        return False, str(e)


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/profiles')
def get_profiles():
    """Get available AWS profiles with their bucket configurations"""
    try:
        # Get AWS profiles from boto3
        session = boto3.Session()
        aws_profiles = session.available_profiles

        # Get bucket configurations from env_config
        profile_configs = get_all_profiles()

        # Merge AWS profiles with configurations
        profiles_with_config = []
        for profile_name in aws_profiles:
            config = get_bucket_config(profile_name)
            profiles_with_config.append({
                'name': profile_name,
                'source_bucket': config.get('source_bucket', ''),
                'destination_bucket': config.get('destination_bucket', ''),
                'description': config.get('description', ''),
                'configured': bool(config.get('source_bucket') and config.get('destination_bucket'))
            })

        return jsonify({'profiles': profiles_with_config})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/profile_config/<profile_name>')
def get_profile_config(profile_name):
    """Get bucket configuration for a specific profile"""
    try:
        config = get_bucket_config(profile_name)
        is_valid, message = validate_profile_config(profile_name)

        return jsonify({
            'profile': profile_name,
            'source_bucket': config.get('source_bucket', ''),
            'destination_bucket': config.get('destination_bucket', ''),
            'description': config.get('description', ''),
            'valid': is_valid,
            'message': message
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/pickle_files')
def get_pickle_files():
    """Get list of existing pickle files"""
    files = [f for f in os.listdir(PICKLE_DIR) if f.endswith('.pkl')]
    files.sort(reverse=True)  # Most recent first
    return jsonify({'files': files})


@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    """Get or update entity configuration"""
    if request.method == 'GET':
        config = load_entity_config()
        return jsonify(config)

    elif request.method == 'POST':
        config = request.json
        save_entity_config(config)
        return jsonify({'success': True})


@app.route('/api/parse_source', methods=['POST'])
def parse_source():
    """Parse source bucket and create pickle file"""
    data = request.json
    profile_name = data.get('profile')
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')

    # Get bucket configuration for this profile
    bucket_config = get_bucket_config(profile_name)
    source_bucket = bucket_config.get('source_bucket', '')

    if not source_bucket:
        return jsonify({'error': f'Source bucket not configured for profile: {profile_name}'}), 400

    # Load config to get entities
    config = load_entity_config()
    entities = list(config.get('entity_mapping', {}).keys())

    if not entities:
        return jsonify({'error': 'No entities configured'}), 400

    try:
        s3_client = get_s3_client(profile_name)
        bucket, prefix = parse_s3_path(source_bucket)

        # Parse dates
        start_date = datetime.fromisoformat(start_date_str) if start_date_str else None
        end_date = datetime.fromisoformat(end_date_str) if end_date_str else None

        # Create pickle file
        pickle_file, df = create_pickle_file(
            s3_client, bucket, entities, start_date, end_date, profile_name
        )

        return jsonify({
            'success': True,
            'pickle_file': os.path.basename(pickle_file),
            'record_count': len(df),
            'source_bucket': source_bucket,
            'preview': df.head(10).to_dict('records')
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/load_pickle', methods=['POST'])
def load_pickle():
    """Load and display pickle file contents"""
    data = request.json
    pickle_file = data.get('pickle_file')

    try:
        df = load_pickle_file(os.path.join(PICKLE_DIR, pickle_file))

        return jsonify({
            'success': True,
            'record_count': len(df),
            'columns': list(df.columns),
            'data': df.to_dict('records')
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/query_pickle', methods=['POST'])
def query_pickle():
    """Query pickle file with filters"""
    data = request.json
    pickle_file = data.get('pickle_file')
    filters = data.get('filters', {})

    try:
        df = load_pickle_file(os.path.join(PICKLE_DIR, pickle_file))

        # Apply filters
        if filters.get('entity_name'):
            df = df[df['entity_name'] == filters['entity_name']]
        if filters.get('dataset'):
            df = df[df['dataset'] == filters['dataset']]
        if filters.get('start_date'):
            date_str = filters['start_date']
            df = df[(df['year'] + df['month'] + df['day']) >= date_str.replace('-', '')]
        if filters.get('end_date'):
            date_str = filters['end_date']
            df = df[(df['year'] + df['month'] + df['day']) <= date_str.replace('-', '')]

        return jsonify({
            'success': True,
            'record_count': len(df),
            'data': df.to_dict('records')
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/copy_to_staging', methods=['POST'])
def copy_to_staging():
    """Copy selected files to staging bucket"""
    data = request.json
    profile_name = data.get('profile')
    records = data.get('records', [])

    # Get bucket configuration for this profile
    bucket_config = get_bucket_config(profile_name)
    source_bucket = bucket_config.get('source_bucket', '')
    dest_bucket = bucket_config.get('destination_bucket', '')

    if not source_bucket or not dest_bucket:
        return jsonify({'error': f'Buckets not configured for profile: {profile_name}'}), 400

    try:
        s3_client = get_s3_client(profile_name)
        source_bucket, _ = parse_s3_path(source_bucket)
        dest_bucket, _ = parse_s3_path(dest_bucket)

        config = load_entity_config()
        cleanup_config = config.get('cleanup_hooks', {})

        results = []

        for record in records:
            entity_name = record['entity_name']
            dataset = record['dataset']
            year = record['year']
            month = record['month']
            day = record['day']
            filename = record['filename']

            # Construct source key
            source_key = f"{entity_name}/{dataset}/year={year}/month={month}/day={day}/{filename}"

            # Execute cleanup hook using CleanupHookManager
            cleanup_success, cleanup_msg = cleanup_manager.execute_cleanup(
                entity_name, dataset, cleanup_config
            )

            if not cleanup_success:
                results.append({
                    'filename': filename,
                    'success': False,
                    'message': f"Cleanup failed: {cleanup_msg}"
                })
                continue

            # Copy file
            copy_success, copy_result = copy_file_to_staging(
                s3_client, source_bucket, source_key, dest_bucket, entity_name, filename
            )

            results.append({
                'filename': filename,
                'success': copy_success,
                'destination': copy_result if copy_success else None,
                'cleanup': cleanup_msg,
                'error': None if copy_success else copy_result
            })

        return jsonify({
            'success': True,
            'results': results,
            'source_bucket': f"s3://{source_bucket}",
            'destination_bucket': f"s3://{dest_bucket}"
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.teardown_appcontext
def cleanup(error=None):
    """Cleanup resources on application teardown"""
    cleanup_manager.close()


if __name__ == '__main__':
    app.run(
        debug=FLASK_CONFIG.get('DEBUG', True),
        host=FLASK_CONFIG.get('HOST', '0.0.0.0'),
        port=FLASK_CONFIG.get('PORT', 7506)
    )