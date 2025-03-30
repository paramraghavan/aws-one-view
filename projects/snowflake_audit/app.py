from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import snowflake.connector
import pandas as pd
from datetime import datetime
import logging
import json
from config import Config
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)
app.secret_key = 'snowflake-monitor-secret-key'

# Initialize configuration
config = Config()
logger = logging.getLogger(__name__)

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.start()
atexit.register(lambda: scheduler.shutdown())


def get_snowflake_connection():
    """Create a connection to Snowflake"""
    try:
        conn_params = config.get_snowflake_config()
        conn = snowflake.connector.connect(
            user=conn_params.get('user'),
            password=conn_params.get('password'),
            account=conn_params.get('account'),
            warehouse=conn_params.get('warehouse'),
            role=conn_params.get('role')
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to Snowflake: {e}")
        return None


def get_schemas_and_tables():
    """Get all databases, schemas and tables from Snowflake"""
    connection = get_snowflake_connection()
    if not connection:
        return {}

    try:
        cursor = connection.cursor()

        # Get configured databases and schemas
        configured_dbs = config.get_databases()
        db_schema_map = {}

        for db_config in configured_dbs:
            db_name = db_config['name']
            db_schema_map[db_name] = {}

            for schema_name in db_config['schemas']:
                # Use the database and schema
                cursor.execute(f'USE DATABASE {db_name}')
                cursor.execute(f'USE SCHEMA {schema_name}')

                # Get all tables in the schema
                cursor.execute(f'SHOW TABLES IN {db_name}.{schema_name}')
                tables = cursor.fetchall()

                # Extract table names from the result
                table_names = [table[1] for table in tables]
                db_schema_map[db_name][schema_name] = table_names

        cursor.close()
        connection.close()
        return db_schema_map

    except Exception as e:
        logger.error(f"Error fetching schemas and tables: {e}")
        if connection:
            connection.close()
        return {}


def check_table_operations(database, schema, table=None, hours=24):
    """Check for CREATE, UPDATE, DELETE operations on tables"""
    connection = get_snowflake_connection()
    if not connection:
        return {"error": "Failed to connect to Snowflake"}

    try:
        cursor = connection.cursor()

        # Set the database and schema context
        cursor.execute(f'USE DATABASE {database}')
        cursor.execute(f'USE SCHEMA {schema}')

        # Get date range for the query
        start_date, end_date = config.get_date_range(hours)

        # Format dates for Snowflake query
        start_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_str = end_date.strftime('%Y-%m-%d %H:%M:%S')

        # Query to get operations from Snowflake query history
        query = f"""
        SELECT 
            QUERY_TEXT,
            DATABASE_NAME,
            SCHEMA_NAME,
            USER_NAME,
            QUERY_TYPE,
            EXECUTION_STATUS,
            START_TIME,
            END_TIME,
            ROWS_PRODUCED,
            ERROR_MESSAGE
        FROM 
            SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
        WHERE 
            START_TIME BETWEEN '{start_str}'::TIMESTAMP_NTZ AND '{end_str}'::TIMESTAMP_NTZ
            AND DATABASE_NAME = '{database}'
            AND SCHEMA_NAME = '{schema}'
            AND QUERY_TYPE IN ('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER')
        """

        # Add table filter if specified
        if table:
            query += f" AND QUERY_TEXT ILIKE '%{table}%'"

        query += " ORDER BY START_TIME DESC"

        cursor.execute(query)
        operations = cursor.fetchall()

        # Convert to list of dictionaries
        column_names = [desc[0] for desc in cursor.description]
        operations_list = []

        for op in operations:
            op_dict = dict(zip(column_names, op))
            # Convert datetime objects to strings for JSON serialization
            for key, value in op_dict.items():
                if isinstance(value, datetime):
                    op_dict[key] = value.strftime('%Y-%m-%d %H:%M:%S')
            operations_list.append(op_dict)

        # Log the findings
        logger.info(
            f"Found {len(operations_list)} operations for {database}.{schema}{' table ' + table if table else ''} in the last {hours} hours")

        cursor.close()
        connection.close()

        return {
            "database": database,
            "schema": schema,
            "table": table,
            "period_hours": hours,
            "start_time": start_str,
            "end_time": end_str,
            "operations_count": len(operations_list),
            "operations": operations_list
        }

    except Exception as e:
        logger.error(f"Error checking table operations: {e}")
        if connection:
            connection.close()
        return {"error": str(e)}


def run_scheduled_check(database, schema, interval):
    """Run scheduled operation check"""
    logger.info(f"Running scheduled check for {database}.{schema} (interval: {interval}h)")
    results = check_table_operations(database, schema, hours=interval)

    if "error" not in results and results["operations_count"] > 0:
        logger.info(f"Scheduled check found {results['operations_count']} operations in {database}.{schema}")

    return results


def schedule_monitoring(selections, intervals):
    """Schedule monitoring jobs for selected schemas"""
    # Clear existing jobs
    scheduler.remove_all_jobs()

    for selection in selections:
        parts = selection.split('.')
        if len(parts) == 2:
            database, schema = parts
            interval = intervals.get(selection, config.get_default_interval())

            # Add job to scheduler
            job_id = f"{database}.{schema}"
            scheduler.add_job(
                func=run_scheduled_check,
                args=[database, schema, interval],
                trigger='interval',
                hours=interval,
                id=job_id,
                replace_existing=True
            )
            logger.info(f"Scheduled monitoring for {database}.{schema} every {interval} hours")

    return len(selections)


@app.route('/')
def index():
    """Main page with schema selection form"""
    db_schema_map = get_schemas_and_tables()
    saved_selections, intervals = config.load_user_selections()

    # Calculate flat list of all database.schema combinations
    all_db_schemas = []
    for db_name, schemas in db_schema_map.items():
        for schema_name in schemas:
            all_db_schemas.append(f"{db_name}.{schema_name}")

    return render_template(
        'index.html',
        db_schema_map=db_schema_map,
        saved_selections=saved_selections,
        intervals=intervals,
        all_db_schemas=all_db_schemas
    )


@app.route('/run-check', methods=['POST'])
def run_check():
    """Run database operations check"""
    selections = request.form.getlist('selections')
    intervals = {}

    # Extract interval values for each selection
    for selection in selections:
        interval_key = f"interval_{selection.replace('.', '_')}"
        if interval_key in request.form:
            intervals[selection] = int(request.form[interval_key])

    # Save user selections if requested
    if 'save_selections' in request.form:
        config.save_user_selections(selections, intervals)

    # Schedule monitoring if requested
    if 'schedule_monitoring' in request.form:
        scheduled_count = schedule_monitoring(selections, intervals)
        flash(f"Scheduled monitoring for {scheduled_count} schemas", "success")

    results = []

    for selection in selections:
        parts = selection.split('.')
        if len(parts) == 2:
            database, schema = parts
            interval = intervals.get(selection, config.get_default_interval())

            # Check for specific table selection
            table_key = f"table_{database}_{schema}"
            table = request.form.get(table_key, None)

            # Run the operation check
            result = check_table_operations(database, schema, table, interval)
            results.append(result)

    return render_template('results.html', results=results)


@app.route('/get-tables', methods=['GET'])
def get_tables():
    """API endpoint to get tables for a specific database and schema"""
    database = request.args.get('database')
    schema = request.args.get('schema')

    if not database or not schema:
        return jsonify({"error": "Database and schema are required"}), 400

    db_schema_map = get_schemas_and_tables()

    if database in db_schema_map and schema in db_schema_map[database]:
        return jsonify({"tables": db_schema_map[database][schema]})
    else:
        return jsonify({"tables": []})


if __name__ == '__main__':
    # Load any saved selections and schedule monitoring
    saved_selections, intervals = config.load_user_selections()
    if saved_selections:
        schedule_monitoring(saved_selections, intervals)

    app.run(debug=True, port=7000)