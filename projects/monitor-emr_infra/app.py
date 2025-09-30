from flask import Flask, render_template, jsonify, request
import yaml
import requests
import pickle
import os
from datetime import datetime, timedelta
from threading import Lock

app = Flask(__name__)

# File paths
CONFIG_FILE = 'emr_config.yaml'
ALERTS_FILE = 'critical_alerts.pkl'

# Thread safety for alerts
alerts_lock = Lock()


def load_config():
    """Load EMR configuration from YAML file"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}


def load_alerts():
    """Load critical alerts from pickle file"""
    try:
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, 'rb') as f:
                return pickle.load(f)
        return []
    except Exception as e:
        print(f"Error loading alerts: {e}")
        return []


def save_alerts(alerts):
    """Save critical alerts to pickle file"""
    try:
        with open(ALERTS_FILE, 'wb') as f:
            pickle.dump(alerts, f)
    except Exception as e:
        print(f"Error saving alerts: {e}")


def get_spark_metrics(spark_url):
    """Get metrics from Spark History Server"""
    try:
        # Get completed applications
        response = requests.get(f"{spark_url}/api/v1/applications", timeout=5)
        if response.status_code == 200:
            apps = response.json()

            completed_jobs = 0
            failed_jobs = 0
            total_memory_used = 0
            total_cpu_used = 0
            app_count = 0

            for app in apps[:10]:  # Last 10 applications
                app_id = app.get('id')

                # Get detailed app info
                try:
                    app_response = requests.get(f"{spark_url}/api/v1/applications/{app_id}", timeout=5)
                    if app_response.status_code == 200:
                        app_detail = app_response.json()
                        attempts = app_detail.get('attempts', [])

                        if attempts:
                            attempt = attempts[0]
                            if attempt.get('completed'):
                                completed_jobs += 1

                            # Check for failures
                            if not attempt.get('completed') or attempt.get('lastUpdated') == attempt.get('endTime'):
                                failed_jobs += 1

                            app_count += 1
                except:
                    pass

            return {
                'completed_jobs': completed_jobs,
                'failed_jobs': failed_jobs,
                'status': 'online'
            }
        return {'status': 'error', 'completed_jobs': 0, 'failed_jobs': 0}
    except Exception as e:
        print(f"Error fetching Spark metrics: {e}")
        return {'status': 'offline', 'completed_jobs': 0, 'failed_jobs': 0}


def get_yarn_metrics(yarn_url):
    """Get metrics from YARN ResourceManager"""
    try:
        # Get cluster metrics
        metrics_response = requests.get(f"{yarn_url}/ws/v1/cluster/metrics", timeout=5)
        nodes_response = requests.get(f"{yarn_url}/ws/v1/cluster/nodes", timeout=5)
        apps_response = requests.get(f"{yarn_url}/ws/v1/cluster/apps", timeout=5)

        metrics = {}

        if metrics_response.status_code == 200:
            cluster_metrics = metrics_response.json().get('clusterMetrics', {})

            # Calculate memory percentage
            total_memory = cluster_metrics.get('totalMB', 1)
            available_memory = cluster_metrics.get('availableMB', 0)
            used_memory = total_memory - available_memory
            memory_percent = (used_memory / total_memory * 100) if total_memory > 0 else 0

            # Calculate CPU percentage (using virtual cores)
            total_vcores = cluster_metrics.get('totalVirtualCores', 1)
            available_vcores = cluster_metrics.get('availableVirtualCores', 0)
            used_vcores = total_vcores - available_vcores
            cpu_percent = (used_vcores / total_vcores * 100) if total_vcores > 0 else 0

            metrics['memory_percent'] = round(memory_percent, 2)
            metrics['cpu_percent'] = round(cpu_percent, 2)
            metrics['total_memory_gb'] = round(total_memory / 1024, 2)
            metrics['used_memory_gb'] = round(used_memory / 1024, 2)
            metrics['total_vcores'] = total_vcores
            metrics['used_vcores'] = used_vcores

        # Get node information
        if nodes_response.status_code == 200:
            nodes = nodes_response.json().get('nodes', {}).get('node', [])

            running_nodes = 0
            lost_nodes = 0
            unhealthy_nodes = 0
            decommissioned_nodes = 0

            for node in nodes:
                state = node.get('state', '')
                health = node.get('nodeHealthStatus', {}).get('nodeHealthReport', '')

                if state == 'RUNNING':
                    running_nodes += 1
                elif state == 'LOST':
                    lost_nodes += 1
                elif state == 'DECOMMISSIONED':
                    decommissioned_nodes += 1

                if 'unhealthy' in health.lower() or node.get('nodeHealthStatus', {}).get('isNodeHealthy') == False:
                    unhealthy_nodes += 1

            metrics['running_nodes'] = running_nodes
            metrics['lost_nodes'] = lost_nodes
            metrics['unhealthy_nodes'] = unhealthy_nodes
            metrics['decommissioned_nodes'] = decommissioned_nodes
            metrics['total_nodes'] = len(nodes)

        # Get application information
        if apps_response.status_code == 200:
            apps = apps_response.json().get('apps', {})
            if apps and 'app' in apps:
                apps_list = apps['app']

                running_apps = sum(1 for app in apps_list if app.get('state') == 'RUNNING')
                accepted_apps = sum(1 for app in apps_list if app.get('state') == 'ACCEPTED')
                submitted_apps = sum(1 for app in apps_list if app.get('state') == 'SUBMITTED')

                metrics['running_apps'] = running_apps
                metrics['accepted_apps'] = accepted_apps
                metrics['submitted_apps'] = submitted_apps
            else:
                metrics['running_apps'] = 0
                metrics['accepted_apps'] = 0
                metrics['submitted_apps'] = 0

        metrics['status'] = 'online'
        return metrics

    except Exception as e:
        print(f"Error fetching YARN metrics: {e}")
        return {
            'status': 'offline',
            'memory_percent': 0,
            'cpu_percent': 0,
            'unhealthy_nodes': 0,
            'running_nodes': 0,
            'lost_nodes': 0,
            'decommissioned_nodes': 0
        }


def check_thresholds(cluster_id, cluster_name, metrics, thresholds):
    """
    Check if ALL THREE critical thresholds are exceeded simultaneously.
    Only creates a critical alert when memory, CPU, AND unhealthy nodes all exceed critical thresholds.
    """
    current_time = datetime.now()

    memory_critical = metrics.get('memory_percent', 0) >= thresholds.get('memory_critical', 90)
    cpu_critical = metrics.get('cpu_percent', 0) >= thresholds.get('cpu_critical', 90)
    nodes_critical = metrics.get('unhealthy_nodes', 0) >= thresholds.get('unhealthy_nodes_critical', 3)

    # Critical alert ONLY when ALL THREE conditions are met
    if memory_critical and cpu_critical and nodes_critical:
        alert = {
            'cluster_id': cluster_id,
            'cluster_name': cluster_name,
            'timestamp': current_time,
            'timestamp_str': current_time.strftime('%Y-%m-%d %H:%M:%S'),
            'memory_value': f"{metrics['memory_percent']}%",
            'cpu_value': f"{metrics['cpu_percent']}%",
            'nodes_value': str(metrics['unhealthy_nodes']),
            'memory_threshold': f"{thresholds['memory_critical']}%",
            'cpu_threshold': f"{thresholds['cpu_critical']}%",
            'nodes_threshold': str(thresholds['unhealthy_nodes_critical']),
            'severity': 'CRITICAL'
        }
        return [alert]

    return []


def get_alert_counts_by_time(cluster_id, alerts):
    """
    Calculate alert counts for different time windows
    Returns counts for: 1 hour, 3 hours, 24 hours, 1 week
    """
    now = datetime.now()

    one_hour_ago = now - timedelta(hours=1)
    three_hours_ago = now - timedelta(hours=3)
    one_day_ago = now - timedelta(days=1)
    one_week_ago = now - timedelta(weeks=1)

    counts = {
        '1h': 0,
        '3h': 0,
        '24h': 0,
        '1w': 0
    }

    for alert in alerts:
        if alert['cluster_id'] != cluster_id:
            continue

        alert_time = alert.get('timestamp')

        # Handle both datetime objects and string timestamps
        if isinstance(alert_time, str):
            try:
                alert_time = datetime.strptime(alert_time, '%Y-%m-%d %H:%M:%S')
            except:
                continue

        if alert_time >= one_hour_ago:
            counts['1h'] += 1
        if alert_time >= three_hours_ago:
            counts['3h'] += 1
        if alert_time >= one_day_ago:
            counts['24h'] += 1
        if alert_time >= one_week_ago:
            counts['1w'] += 1

    return counts


@app.route('/')
def index():
    """Render main dashboard"""
    return render_template('index.html')


@app.route('/api/clusters')
def get_clusters():
    """API endpoint to get all cluster metrics"""
    config = load_config()
    clusters_data = []

    for cluster_id, cluster_config in config.items():
        if cluster_id in ['memory_warning', 'memory_critical', 'cpu_warning',
                          'cpu_critical', 'unhealthy_nodes_warning', 'unhealthy_nodes_critical']:
            continue

        # Get Spark metrics
        spark_metrics = get_spark_metrics(cluster_config['spark_url'])

        # Get YARN metrics
        yarn_metrics = get_yarn_metrics(cluster_config['yarn_url'])

        # Check thresholds
        thresholds = {
            'memory_warning': config.get('memory_warning', 80),
            'memory_critical': config.get('memory_critical', 90),
            'cpu_warning': config.get('cpu_warning', 80),
            'cpu_critical': config.get('cpu_critical', 90),
            'unhealthy_nodes_warning': config.get('unhealthy_nodes_warning', 1),
            'unhealthy_nodes_critical': config.get('unhealthy_nodes_critical', 3)
        }

        new_alerts = check_thresholds(cluster_id, cluster_config['name'], yarn_metrics, thresholds)

        # Add new alerts to storage
        if new_alerts:
            with alerts_lock:
                all_alerts = load_alerts()
                all_alerts.extend(new_alerts)
                save_alerts(all_alerts)

        # Get alert counts by time window
        with alerts_lock:
            all_alerts = load_alerts()
            alert_counts = get_alert_counts_by_time(cluster_id, all_alerts)

        # Determine overall status
        status = 'healthy'
        if (yarn_metrics.get('memory_percent', 0) >= thresholds['memory_critical'] and
                yarn_metrics.get('cpu_percent', 0) >= thresholds['cpu_critical'] and
                yarn_metrics.get('unhealthy_nodes', 0) >= thresholds['unhealthy_nodes_critical']):
            status = 'critical'
        elif (yarn_metrics.get('memory_percent', 0) >= thresholds['memory_warning'] or
              yarn_metrics.get('cpu_percent', 0) >= thresholds['cpu_warning'] or
              yarn_metrics.get('unhealthy_nodes', 0) >= thresholds['unhealthy_nodes_warning']):
            status = 'warning'

        clusters_data.append({
            'id': cluster_id,
            'name': cluster_config['name'],
            'description': cluster_config.get('description', ''),
            'spark_url': cluster_config['spark_url'],
            'yarn_url': cluster_config['yarn_url'],
            'spark_metrics': spark_metrics,
            'yarn_metrics': yarn_metrics,
            'thresholds': thresholds,
            'alert_counts': alert_counts,
            'status': status
        })

    return jsonify(clusters_data)


@app.route('/api/alerts')
def get_alerts():
    """API endpoint to get all critical alerts"""
    with alerts_lock:
        alerts = load_alerts()

    # Convert datetime objects to strings for JSON serialization
    serializable_alerts = []
    for alert in alerts:
        alert_copy = alert.copy()
        if isinstance(alert_copy.get('timestamp'), datetime):
            alert_copy['timestamp'] = alert_copy['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
        serializable_alerts.append(alert_copy)

    return jsonify(serializable_alerts)


@app.route('/api/clear_alerts', methods=['POST'])
def clear_alerts():
    """API endpoint to clear all alerts and reset monitoring"""
    try:
        with alerts_lock:
            save_alerts([])
        return jsonify({'success': True, 'message': 'All alerts cleared successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7501)