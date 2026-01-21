"""
Snowflake Resource Monitor - Flask Application
A comprehensive tool for Snowflake administrators to monitor costs, 
performance bottlenecks, and resource utilization.
"""

from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# ============================================================
# MOCK MODE - Set to True to use fake data (no Snowflake needed)
# ============================================================
USE_MOCK = os.environ.get('USE_MOCK', 'false').lower() == 'true'

# Import the appropriate connector based on mode
if USE_MOCK:
    from mock_connector import MockSnowflakeMonitor as SnowflakeMonitor
    print("🔶 Running in MOCK MODE - using simulated data")
else:
    from snowflake_connector import SnowflakeMonitor
    print("🔷 Running in LIVE MODE - connecting to Snowflake")

# Configuration - Set these environment variables or modify directly
SNOWFLAKE_CONFIG = {
    'account': os.environ.get('SNOWFLAKE_ACCOUNT', 'your_account'),
    'user': os.environ.get('SNOWFLAKE_USER', 'your_user'),
    'password': os.environ.get('SNOWFLAKE_PASSWORD', 'your_password'),
    'warehouse': os.environ.get('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
    'database': os.environ.get('SNOWFLAKE_DATABASE', 'SNOWFLAKE'),
    'schema': os.environ.get('SNOWFLAKE_SCHEMA', 'ACCOUNT_USAGE'),
    'role': os.environ.get('SNOWFLAKE_ROLE', 'ACCOUNTADMIN')
}


def get_monitor():
    """Get a Snowflake monitor instance."""
    return SnowflakeMonitor(SNOWFLAKE_CONFIG)


@app.route('/')
def dashboard():
    """Main dashboard view."""
    return render_template('dashboard.html')


@app.route('/api/overview')
def api_overview():
    """Get overview metrics."""
    try:
        monitor = get_monitor()
        data = monitor.get_overview_metrics()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/warehouse-costs')
def api_warehouse_costs():
    """Get warehouse cost breakdown."""
    days = request.args.get('days', 30, type=int)
    try:
        monitor = get_monitor()
        data = monitor.get_warehouse_costs(days)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/warehouse-usage')
def api_warehouse_usage():
    """Get warehouse usage statistics."""
    days = request.args.get('days', 7, type=int)
    try:
        monitor = get_monitor()
        data = monitor.get_warehouse_usage(days)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/long-running-queries')
def api_long_running_queries():
    """Get long-running queries."""
    threshold_seconds = request.args.get('threshold', 60, type=int)
    limit = request.args.get('limit', 50, type=int)
    try:
        monitor = get_monitor()
        data = monitor.get_long_running_queries(threshold_seconds, limit)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/expensive-queries')
def api_expensive_queries():
    """Get most expensive queries by credits."""
    days = request.args.get('days', 7, type=int)
    limit = request.args.get('limit', 50, type=int)
    try:
        monitor = get_monitor()
        data = monitor.get_expensive_queries(days, limit)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/storage-usage')
def api_storage_usage():
    """Get storage usage by database."""
    try:
        monitor = get_monitor()
        data = monitor.get_storage_usage()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/cluster-load')
def api_cluster_load():
    """Get cluster load and concurrency metrics."""
    days = request.args.get('days', 7, type=int)
    try:
        monitor = get_monitor()
        data = monitor.get_cluster_load(days)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/warehouse-config')
def api_warehouse_config():
    """Get warehouse configurations including suspend settings."""
    try:
        monitor = get_monitor()
        data = monitor.get_warehouse_configurations()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/query-patterns')
def api_query_patterns():
    """Analyze query patterns for bottlenecks."""
    days = request.args.get('days', 7, type=int)
    try:
        monitor = get_monitor()
        data = monitor.analyze_query_patterns(days)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/cost-trends')
def api_cost_trends():
    """Get cost trends over time."""
    days = request.args.get('days', 30, type=int)
    try:
        monitor = get_monitor()
        data = monitor.get_cost_trends(days)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/bottleneck-analysis')
def api_bottleneck_analysis():
    """Get comprehensive bottleneck analysis."""
    try:
        monitor = get_monitor()
        data = monitor.analyze_bottlenecks()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/database-costs')
def api_database_costs():
    """Get cost breakdown by database."""
    days = request.args.get('days', 30, type=int)
    try:
        monitor = get_monitor()
        data = monitor.get_database_costs(days)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/recommendations')
def api_recommendations():
    """Get optimization recommendations."""
    try:
        monitor = get_monitor()
        data = monitor.get_recommendations()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/queued-queries')
def api_queued_queries():
    """Get information about queued queries (concurrency bottlenecks)."""
    days = request.args.get('days', 7, type=int)
    try:
        monitor = get_monitor()
        data = monitor.get_queued_queries(days)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/credit-usage-hourly')
def api_credit_usage_hourly():
    """Get hourly credit usage pattern."""
    days = request.args.get('days', 7, type=int)
    try:
        monitor = get_monitor()
        data = monitor.get_hourly_credit_usage(days)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
