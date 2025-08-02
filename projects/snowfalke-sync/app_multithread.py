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
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
from threading import Lock

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
log_lock = Lock()  # Thread-safe logging

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
    """Add a new entry to the sync log (thread-safe)"""
    global sync_log

    with log_lock:  # Ensure thread-safe access to DataFrame
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


def get_table_row_count(cursor, table_name):
    """Get the total number of rows in a table"""
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        result = cursor.fetchone()
        return result[0] if result else 0
    except Exception as e:
        logger.warning(f"Could not get row count for {table_name}: {e}")
        return None


def get_table_columns(cursor, table_name):
    """Get column information for a table"""
    try:
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 0")
        return [desc[0] for desc in cursor.description]
    except Exception as e:
        logger.error(f"Could not get columns for {table_name}: {e}")
        raise


def sync_table_chunk(source_config, target_config, table_name, columns, offset, chunk_size, chunk_number, total_rows,
                     insert_queue):
    """Sync a single chunk of data from source to target"""
    records_synced = 0

    try:
        # Connect to source database and read chunk
        with get_snowflake_connection(source_config) as source_conn:
            source_cursor = source_conn.cursor()

            chunk_query = f"SELECT * FROM {table_name} LIMIT {chunk_size} OFFSET {offset}"
            logger.debug(f"Reading chunk {chunk_number} for {table_name}: LIMIT {chunk_size} OFFSET {offset}")

            source_cursor.execute(chunk_query)
            chunk_data = source_cursor.fetchall()

            if not chunk_data:
                logger.debug(f"No data in chunk {chunk_number} for {table_name}")
                return 0

            # Add chunk to the write queue
            insert_queue.put({
                'data': chunk_data,
                'chunk_number': chunk_number,
                'table_name': table_name
            })

            records_synced = len(chunk_data)

            # Progress logging
            if total_rows:
                progress_pct = ((offset + records_synced) / total_rows) * 100
                logger.info(
                    f"Read chunk {chunk_number} for {table_name}: {records_synced:,} rows ({progress_pct:.1f}% total)")
            else:
                logger.info(f"Read chunk {chunk_number} for {table_name}: {records_synced:,} rows")

            return records_synced

    except Exception as e:
        logger.error(f"Error reading chunk {chunk_number} for table {table_name}: {e}")
        # Add poison pill to queue to signal error
        insert_queue.put({
            'error': str(e),
            'chunk_number': chunk_number,
            'table_name': table_name
        })
        raise


def sync_table_writer(target_config, table_name, columns, insert_queue, total_chunks):
    """Writer thread that processes chunks from the queue and writes to target database"""
    total_records_written = 0
    chunks_processed = 0

    try:
        with get_snowflake_connection(target_config) as target_conn:
            target_cursor = target_conn.cursor()

            # Prepare insert statement
            placeholders = ', '.join(['%s'] * len(columns))
            insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

            while chunks_processed < total_chunks:
                try:
                    # Get chunk from queue (timeout to avoid hanging)
                    chunk_item = insert_queue.get(timeout=300)  # 5 minute timeout

                    # Check for error in chunk
                    if 'error' in chunk_item:
                        logger.error(f"Received error chunk for {table_name}: {chunk_item['error']}")
                        chunks_processed += 1
                        continue

                    chunk_data = chunk_item['data']
                    chunk_number = chunk_item['chunk_number']

                    # Insert chunk data in smaller batches
                    insert_batch_size = 1000
                    chunk_records = 0

                    for i in range(0, len(chunk_data), insert_batch_size):
                        batch = chunk_data[i:i + insert_batch_size]
                        target_cursor.executemany(insert_query, batch)
                        chunk_records += len(batch)

                    # Commit the chunk
                    target_conn.commit()
                    total_records_written += chunk_records
                    chunks_processed += 1

                    logger.info(
                        f"Written chunk {chunk_number} for {table_name}: {chunk_records:,} rows (Total: {total_records_written:,})")

                    insert_queue.task_done()

                except queue.Empty:
                    logger.warning(f"Timeout waiting for chunk data for {table_name}")
                    break
                except Exception as e:
                    logger.error(f"Error writing chunk for {table_name}: {e}")
                    chunks_processed += 1
                    continue

            logger.info(f"Writer completed for {table_name}: {total_records_written:,} total records written")
            return total_records_written

    except Exception as e:
        logger.error(f"Error in writer thread for {table_name}: {e}")
        raise


def sync_table_multithreaded(source_config, target_config, table_name):
    """Sync a table using multiple threads for reading and writing"""
    records_synced = 0
    chunk_size = config.get('chunk_size', 10000)
    max_workers = config.get('max_workers', 4)  # Number of reader threads
    use_multithreading = config.get('use_multithreading', True)
    multithreading_threshold = config.get('multithreading_threshold', 500000)

    logger.info(f"Starting sync for table {table_name}")

    try:
        # Get table info
        with get_snowflake_connection(source_config) as source_conn:
            source_cursor = source_conn.cursor()

            columns = get_table_columns(source_cursor, table_name)
            total_rows = get_table_row_count(source_cursor, table_name)

            if total_rows == 0:
                add_log_entry(source_config['database'], target_config['database'],
                              table_name, 'SUCCESS', 0, 'No data to sync')
                return

            logger.info(f"Table {table_name} has {total_rows:,} rows, {len(columns)} columns")

            # Decide whether to use multithreading
            should_multithread = use_multithreading and total_rows >= multithreading_threshold

            if should_multithread:
                logger.info(
                    f"Using multithreaded sync for {table_name} ({total_rows:,} rows >= {multithreading_threshold:,} threshold)")
            else:
                logger.info(
                    f"Using single-threaded sync for {table_name} ({total_rows:,} rows < {multithreading_threshold:,} threshold)")

        # Clear target table
        with get_snowflake_connection(target_config) as target_conn:
            target_cursor = target_conn.cursor()
            target_cursor.execute(f"TRUNCATE TABLE {table_name}")
            target_conn.commit()
            logger.info(f"Truncated target table {table_name}")

        if should_multithread:
            # Multithreaded approach
            records_synced = sync_table_multithreaded_impl(
                source_config, target_config, table_name, columns,
                total_rows, chunk_size, max_workers
            )
        else:
            # Single-threaded approach (original method)
            records_synced = sync_table_single_threaded(
                source_config, target_config, table_name, columns,
                total_rows, chunk_size
            )

        add_log_entry(source_config['database'], target_config['database'],
                      table_name, 'SUCCESS', records_synced)
        logger.info(f"Successfully synced {records_synced:,} records for table {table_name}")

    except Exception as e:
        error_msg = str(e)
        add_log_entry(source_config['database'], target_config['database'],
                      table_name, 'ERROR', records_synced, error_msg)
        logger.error(f"Error syncing table {table_name}: {error_msg}")


def sync_table_multithreaded_impl(source_config, target_config, table_name, columns, total_rows, chunk_size,
                                  max_workers):
    """Multithreaded implementation of table sync"""
    # Create queue for chunks to be written
    insert_queue = queue.Queue(maxsize=max_workers * 2)  # Limit queue size

    # Calculate chunks
    total_chunks = (total_rows + chunk_size - 1) // chunk_size
    logger.info(f"Processing {total_chunks} chunks of {chunk_size:,} rows each for {table_name}")

    # Start writer thread
    writer_thread = threading.Thread(
        target=sync_table_writer,
        args=(target_config, table_name, columns, insert_queue, total_chunks),
        name=f"Writer-{table_name}"
    )
    writer_thread.start()

    total_records_read = 0

    # Use ThreadPoolExecutor for reader threads
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=f"Reader-{table_name}") as executor:
        # Submit reader tasks
        future_to_chunk = {}

        for chunk_num in range(total_chunks):
            if should_stop:
                break

            offset = chunk_num * chunk_size
            future = executor.submit(
                sync_table_chunk,
                source_config, target_config, table_name, columns,
                offset, chunk_size, chunk_num + 1, total_rows, insert_queue
            )
            future_to_chunk[future] = chunk_num + 1

        # Process completed reader tasks
        for future in as_completed(future_to_chunk):
            chunk_num = future_to_chunk[future]
            try:
                records_read = future.result()
                total_records_read += records_read
            except Exception as e:
                logger.error(f"Reader thread for chunk {chunk_num} failed: {e}")

    # Wait for writer to complete
    writer_thread.join(timeout=1800)  # 30 minute timeout

    if writer_thread.is_alive():
        logger.error(f"Writer thread for {table_name} did not complete within timeout")

    logger.info(f"Multithreaded sync completed for {table_name}: {total_records_read:,} records processed")
    return total_records_read


def sync_table_single_threaded(source_config, target_config, table_name, columns, total_rows, chunk_size):
    """Single-threaded implementation of table sync (original method)"""
    records_synced = 0

    with get_snowflake_connection(target_config) as target_conn:
        target_cursor = target_conn.cursor()

        placeholders = ', '.join(['%s'] * len(columns))
        insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

        offset = 0
        chunk_number = 1

        while True:
            if should_stop:
                break

            # Read chunk from source
            with get_snowflake_connection(source_config) as source_conn:
                source_cursor = source_conn.cursor()
                chunk_query = f"SELECT * FROM {table_name} LIMIT {chunk_size} OFFSET {offset}"
                source_cursor.execute(chunk_query)
                chunk_data = source_cursor.fetchall()

            if not chunk_data:
                break

            # Write chunk to target
            insert_batch_size = 1000
            for i in range(0, len(chunk_data), insert_batch_size):
                batch = chunk_data[i:i + insert_batch_size]
                target_cursor.executemany(insert_query, batch)

            target_conn.commit()
            records_synced += len(chunk_data)

            # Progress logging
            if total_rows:
                progress_pct = (records_synced / total_rows) * 100
                logger.info(f"Progress for {table_name}: {records_synced:,}/{total_rows:,} ({progress_pct:.1f}%)")

            offset += len(chunk_data)
            chunk_number += 1

            if len(chunk_data) < chunk_size:
                break

            time.sleep(0.1)  # Small delay

    return records_synced


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
            sync_table_multithreaded(source_config, target_config, table_name)

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


# Add a simple test route to verify Flask is working
@app.route('/')
def index():
    """Main dashboard page"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering template: {e}")
        # Return a simple HTML page if template fails
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Snowflake Sync Dashboard</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #f0f0f0; }
                .container { background: white; padding: 30px; border-radius: 10px; }
                .error { color: #e74c3c; }
                .info { color: #666; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Snowflake Database Sync</h1>
                <div class="error">Template loading error. Please check if templates/index.html exists.</div>
                <div class="info">
                    <strong>Quick Tests:</strong><br>
                    • <a href="/test">Test Page</a><br>
                    • <a href="/health">Health Check</a><br>
                    • <a href="/api/stats">Stats API</a><br>
                </div>
            </div>
        </body>
        </html>
        '''


@app.route('/test')
def test_page():
    """Simple test page"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Snowflake Sync - Test Page</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f0f0f0; }
            .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .success { color: #27ae60; font-size: 24px; font-weight: bold; }
            .info { color: #666; margin: 20px 0; }
            .link { color: #3498db; text-decoration: none; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="success">✅ Flask Application is Working!</div>
            <div class="info">If you can see this page, Flask is running correctly on port 5000.</div>
            <div class="info">
                <a href="/" class="link">Go to Main Dashboard →</a>
            </div>
            <div class="info">
                <strong>Available URLs:</strong><br>
                • <a href="/" class="link">http://localhost:5000/</a> - Main Dashboard<br>
                • <a href="/health" class="link">http://localhost:5000/health</a> - Health Check<br>
                • <a href="/api/stats" class="link">http://localhost:5000/api/stats</a> - Stats API<br>
            </div>
        </div>
    </body>
    </html>
    '''


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

        # Print startup information
        print("=" * 60)
        print("🚀 Snowflake Database Sync Dashboard Starting...")
        print("=" * 60)
        print(f"📊 Dashboard URL: http://localhost:5000")
        print(f"📊 Dashboard URL: http://127.0.0.1:5000")
        print(f"📊 Network URL: http://0.0.0.0:5000")
        print("=" * 60)
        print("📋 Available endpoints:")
        print("   • GET  /                 - Main dashboard")
        print("   • GET  /api/logs         - Sync logs JSON")
        print("   • GET  /api/stats        - Statistics JSON")
        print("   • GET  /api/sync/start   - Start auto-sync")
        print("   • GET  /api/sync/stop    - Stop auto-sync")
        print("   • GET  /api/sync/manual  - Manual sync")
        print("=" * 60)
        print("🔧 Press Ctrl+C to stop the application")
        print("=" * 60)

        # Run Flask app with more explicit settings
        app.run(
            debug=False,  # Disable debug mode to prevent reload issues
            host='0.0.0.0',  # Listen on all interfaces
            port=5000,  # Explicit port
            use_reloader=False,  # Disable auto-reloader
            threaded=True  # Enable threading for better performance
        )

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        print(f"❌ Error starting application: {e}")
    finally:
        stop_sync_scheduler()
        save_sync_log()