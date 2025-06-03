from flask import Flask, render_template, jsonify
import pandas as pd
import snowflake.connector
import yaml
import threading
import time
import os
import pickle
from datetime import datetime, timedelta
import logging
from contextlib import contextmanager
import signal
import sys

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'

# Global variables
sync_log = pd.DataFrame(columns=[
    'timestamp', 'source_db', 'target_db', 'table_name',
    'status', 'records_synced', 'error_message'
])
sync_thread = None
should_stop = False
config = {}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from YAML file"""
    global config
    try:
        with open('config.yaml', 'r') as file:
            config = yaml.safe_load(file)
        logger.info("Configuration loaded successfully")
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise


def load_sync_log():
    """Load sync log from pickle file"""
    global sync_log
    pickle_file = config.get('logging', {}).get('pickle_file', 'sync_log.pkl')

    if os.path.exists(pickle_file):
        try:
            sync_log = pd.read_pickle(pickle_file)
            logger.info(f"Loaded {len(sync_log)} log records from {pickle_file}")
        except Exception as e:
            logger.error(f"Error loading pickle file: {e}")
            sync_log = pd.DataFrame(columns=[
                'timestamp', 'source_db', 'target_db', 'table_name',
                'status', 'records_synced', 'error_message'
            ])
    else:
        logger.info("No existing pickle file found, starting with empty log")


def save_sync_log():
    """Save sync log to pickle file"""
    global sync_log
    pickle_file = config.get('logging', {}).get('pickle_file', 'sync_log.pkl')

    try:
        # Limit the number of records to prevent memory issues
        max_records = config.get('logging', {}).get('max_records', 10000)
        if len(sync_log) > max_records:
            sync_log = sync_log.tail(max_records)

        sync_log.to_pickle(pickle_file)
        logger.info(f"Saved {len(sync_log)} log records to {pickle_file}")
    except Exception as e:
        logger.error(f"Error saving pickle file: {e}")


def add_log_entry(source_db, target_db, table_name, status, records_synced=0, error_message=None):
    """Add a new entry to the sync log"""
    global sync_log

    new_entry = pd.DataFrame({
        'timestamp': [datetime.now()],
        'source_db': [source_db],
        'target_db': [target_db],
        'table_name': [table_name],
        'status': [status],
        'records_synced': [records_synced],
        'error_message': [error_message]
    })

    sync_log = pd.concat([sync_log, new_entry], ignore_index=True)


@contextmanager
def get_snowflake_connection(db_config):
    """Context manager for Snowflake connections"""
    conn = None
    try:
        conn = snowflake.connector.connect(
            account=db_config['account'],
            user=db_config['user'],
            password=db_config['password'],
            warehouse=db_config['warehouse'],
            database=db_config['database'],
            schema=db_config['schema']
        )
        yield conn
    except Exception as e:
        logger.error(f"Connection error: {e}")
        raise
    finally:
        if conn:
            conn.close()


def sync_table(source_config, target_config, table_name):
    """Sync a single table from source to target"""
    records_synced = 0

    try:
        # Connect to source database
        with get_snowflake_connection(source_config) as source_conn:
            source_cursor = source_conn.cursor()

            # Get table data from source
            source_cursor.execute(f"SELECT * FROM {table_name}")
            source_data = source_cursor.fetchall()
            columns = [desc[0] for desc in source_cursor.description]

            if not source_data:
                add_log_entry(
                    source_config['database'],
                    target_config['database'],
                    table_name,
                    'SUCCESS',
                    0,
                    'No data to sync'
                )
                return

            # Connect to target database
            with get_snowflake_connection(target_config) as target_conn:
                target_cursor = target_conn.cursor()

                # Truncate target table (you might want to modify this logic)
                target_cursor.execute(f"TRUNCATE TABLE {table_name}")

                # Prepare insert statement
                placeholders = ', '.join(['%s'] * len(columns))
                insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

                # Insert data in batches
                batch_size = 1000
                for i in range(0, len(source_data), batch_size):
                    batch = source_data[i:i + batch_size]
                    target_cursor.executemany(insert_query, batch)
                    records_synced += len(batch)

                target_conn.commit()

                add_log_entry(
                    source_config['database'],
                    target_config['database'],
                    table_name,
                    'SUCCESS',
                    records_synced
                )

                logger.info(f"Successfully synced {records_synced} records for table {table_name}")

    except Exception as e:
        error_msg = str(e)
        add_log_entry(
            source_config['database'],
            target_config['database'],
            table_name,
            'ERROR',
            records_synced,
            error_msg
        )
        logger.error(f"Error syncing table {table_name}: {error_msg}")


def sync_databases():
    """Sync all configured databases"""
    logger.info("Starting database sync process")

    for db_pair in config.get('databases', []):
        source_config = db_pair['source']
        target_config = db_pair['target']
        tables = db_pair['tables']

        for table_name in tables:
            if should_stop:
                break
            sync_table(source_config, target_config, table_name)

    logger.info("Database sync process completed")


def sync_scheduler():
    """Background thread for scheduled syncing"""
    global should_stop

    sync_interval = config.get('sync_interval_minutes', 60) * 60  # Convert to seconds

    while not should_stop:
        try:
            sync_databases()
            save_sync_log()  # Save after each sync cycle

            # Wait for next sync or until stop signal
            for _ in range(sync_interval):
                if should_stop:
                    break
                time.sleep(1)

        except Exception as e:
            logger.error(f"Error in sync scheduler: {e}")
            time.sleep(60)  # Wait 1 minute before retrying


def start_sync_scheduler():
    """Start the background sync scheduler"""
    global sync_thread

    if sync_thread is None or not sync_thread.is_alive():
        sync_thread = threading.Thread(target=sync_scheduler, daemon=True)
        sync_thread.start()
        logger.info("Sync scheduler started")


def stop_sync_scheduler():
    """Stop the background sync scheduler"""
    global should_stop, sync_thread

    should_stop = True
    if sync_thread and sync_thread.is_alive():
        sync_thread.join(timeout=5)
    logger.info("Sync scheduler stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info("Received shutdown signal, saving data...")
    stop_sync_scheduler()
    save_sync_log()
    sys.exit(0)


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')


@app.route('/api/logs')
def get_logs():
    """API endpoint to get sync logs"""
    global sync_log

    # Convert DataFrame to JSON
    logs_json = sync_log.to_dict('records')

    # Format timestamps for JSON serialization
    for log in logs_json:
        if 'timestamp' in log and pd.notna(log['timestamp']):
            log['timestamp'] = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify(logs_json)


@app.route('/api/stats')
def get_stats():
    """API endpoint to get sync statistics"""
    global sync_log

    if sync_log.empty:
        return jsonify({
            'total_syncs': 0,
            'successful_syncs': 0,
            'failed_syncs': 0,
            'last_sync': None
        })

    stats = {
        'total_syncs': len(sync_log),
        'successful_syncs': len(sync_log[sync_log['status'] == 'SUCCESS']),
        'failed_syncs': len(sync_log[sync_log['status'] == 'ERROR']),
        'last_sync': sync_log['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S') if not sync_log.empty else None
    }

    return jsonify(stats)


@app.route('/api/sync/start')
def start_sync():
    """API endpoint to manually start sync"""
    start_sync_scheduler()
    return jsonify({'status': 'started'})


@app.route('/api/sync/stop')
def stop_sync():
    """API endpoint to stop sync"""
    stop_sync_scheduler()
    return jsonify({'status': 'stopped'})


@app.route('/api/sync/manual')
def manual_sync():
    """API endpoint to trigger manual sync"""
    try:
        sync_databases()
        save_sync_log()
        return jsonify({'status': 'completed'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


if __name__ == '__main__':
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Load configuration and sync log
        load_config()
        load_sync_log()

        # Start the sync scheduler
        start_sync_scheduler()

        # Run Flask app
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    finally:
        stop_sync_scheduler()
        save_sync_log()