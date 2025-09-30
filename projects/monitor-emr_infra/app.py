from flask import Flask, render_template, jsonify, request
import yaml
import requests
import pickle
import os
from datetime import datetime
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
    """Check if metrics exceed critical thresholds and log alerts"""
    alerts = []
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Check memory threshold
    if metrics.get('memory_percent', 0) >= thresholds.get('memory_critical', 90):
        alerts.append({
            'cluster_id': cluster_id,
            'cluster_name': cluster_name,
            'timestamp': current_time,
            'type': 'Memory',
            'value': f"{metrics['memory_percent']}%",
            'threshold': f"{thresholds['memory_critical']}%",
            'severity': 'CRITICAL'
        })

    # Check CPU threshold
    if metrics.get('cpu_percent', 0) >= thresholds.get('cpu_critical', 90):
        alerts.append({
            'cluster_id': cluster_id,
            'cluster_name': cluster_name,
            'timestamp': current_time,
            'type': 'CPU',
            'value': f"{metrics['cpu_percent']}%",
            'threshold': f"{thresholds['cpu_critical']}%",
            'severity': 'CRITICAL'
        })

    # Check unhealthy nodes threshold
    unhealthy = metrics.get('unhealthy_nodes', 0)
    if unhealthy >= thresholds.get('unhealthy_nodes_critical', 3):
        alerts.append({
            'cluster_id': cluster_id,
            'cluster_name': cluster_name,
            'timestamp': current_time,
            'type': 'Unhealthy Nodes',
            'value': str(unhealthy),
            'threshold': str(thresholds['unhealthy_nodes_critical']),
            'severity': 'CRITICAL'
        })

    return alerts


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

        # Count critical alerts for this cluster
        with alerts_lock:
            all_alerts = load_alerts()
            critical_count = sum(1 for alert in all_alerts if alert['cluster_id'] == cluster_id)

        # Determine overall status
        status = 'healthy'
        if (yarn_metrics.get('memory_percent', 0) >= thresholds['memory_critical'] or
                yarn_metrics.get('cpu_percent', 0) >= thresholds['cpu_critical'] or
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
            'critical_count': critical_count,
            'status': status
        })

    return jsonify(clusters_data)


@app.route('/api/alerts')
def get_alerts():
    """API endpoint to get all critical alerts"""
    with alerts_lock:
        alerts = load_alerts()
    return jsonify(alerts)


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